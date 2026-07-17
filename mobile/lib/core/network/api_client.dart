import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

import '../config/app_config.dart';
import 'token_store.dart';

class ApiException implements Exception {
  const ApiException(this.message,
      {this.code = 'request_failed', this.retryable = false});

  final String message;
  final String code;
  final bool retryable;

  @override
  String toString() => message;
}

String apiErrorMessage(Object error) {
  if (error is ApiException) return error.message;
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map) {
      final detail = data['detail'];
      if (detail is String && detail.trim().isNotEmpty) return detail;
      if (detail is List && detail.isNotEmpty) {
        final messages = detail
            .map((item) => item is Map ? item['msg'] : item)
            .whereType<Object>()
            .map((item) => item.toString())
            .where((item) => item.isNotEmpty)
            .toList();
        if (messages.isNotEmpty) return messages.join('\n');
      }
      final message = data['message'];
      if (message is String && message.trim().isNotEmpty) return message;
    }
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return '连接服务器超时，请检查网络后重试。';
      case DioExceptionType.connectionError:
        return '无法连接服务器，请检查手机网络。';
      default:
        break;
    }
    final statusCode = error.response?.statusCode;
    if (statusCode != null) return '服务器请求失败（$statusCode）。';
  }
  return '操作失败，请稍后重试。';
}

class ApiClient {
  ApiClient(this.tokenStore)
      : dio = Dio(
          BaseOptions(
            baseUrl: AppConfig.apiBaseUrl,
            connectTimeout: const Duration(seconds: 15),
            receiveTimeout: const Duration(minutes: 3),
            headers: {'Accept': 'application/json'},
          ),
        ) {
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await tokenStore.readAccessToken();
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: _refreshAndRetry,
      ),
    );
  }

  final TokenStore tokenStore;
  final Dio dio;
  Future<void>? _refreshing;

  Future<void> _refreshAndRetry(
      DioException error, ErrorInterceptorHandler handler) async {
    final request = error.requestOptions;
    if (error.response?.statusCode != 401 ||
        request.extra['retried'] == true ||
        request.path.contains('/auth/refresh')) {
      handler.next(error);
      return;
    }
    final refreshToken = await tokenStore.readRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      await tokenStore.clear();
      handler.next(error);
      return;
    }
    try {
      _refreshing ??= _refresh(refreshToken);
      await _refreshing;
      request.extra['retried'] = true;
      final accessToken = await tokenStore.readAccessToken();
      request.headers['Authorization'] = 'Bearer $accessToken';
      handler.resolve(await dio.fetch<dynamic>(request));
    } catch (_) {
      await tokenStore.clear();
      handler.next(error);
    } finally {
      _refreshing = null;
    }
  }

  Future<void> _refresh(String refreshToken) async {
    final refreshDio = Dio(BaseOptions(baseUrl: AppConfig.apiBaseUrl));
    final response = await refreshDio.post<Map<String, dynamic>>(
      '/auth/refresh',
      data: {'refresh_token': refreshToken},
    );
    await tokenStore.saveSession(response.data!);
  }

  Future<Map<String, dynamic>> getJson(String path,
      {Map<String, dynamic>? query}) async {
    final response =
        await dio.get<Map<String, dynamic>>(path, queryParameters: query);
    return response.data ?? <String, dynamic>{};
  }

  Future<List<dynamic>> getList(String path,
      {Map<String, dynamic>? query}) async {
    final response = await dio.get<List<dynamic>>(path, queryParameters: query);
    return response.data ?? <dynamic>[];
  }

  Future<Map<String, dynamic>> postJson(
    String path, [
    Map<String, dynamic>? body,
    Map<String, dynamic>? query,
  ]) async {
    final response = await dio.post<Map<String, dynamic>>(path,
        data: body, queryParameters: query);
    return response.data ?? <String, dynamic>{};
  }

  Future<Map<String, dynamic>> patchJson(
      String path, Map<String, dynamic> body) async {
    final response = await dio.patch<Map<String, dynamic>>(path, data: body);
    return response.data ?? <String, dynamic>{};
  }

  Future<Map<String, dynamic>> putJson(
      String path, Map<String, dynamic> body) async {
    final response = await dio.put<Map<String, dynamic>>(path, data: body);
    return response.data ?? <String, dynamic>{};
  }

  Future<Map<String, dynamic>> deleteJson(String path,
      {Map<String, dynamic>? query}) async {
    final response =
        await dio.delete<Map<String, dynamic>>(path, queryParameters: query);
    return response.data ?? <String, dynamic>{};
  }

  Future<Map<String, dynamic>> uploadFile(String path, String filePath,
      {String field = 'file'}) async {
    final form =
        FormData.fromMap({field: await MultipartFile.fromFile(filePath)});
    final response = await dio.post<Map<String, dynamic>>(path, data: form);
    return response.data ?? <String, dynamic>{};
  }

  Stream<Map<String, dynamic>> postNdjson(
    String path,
    Map<String, dynamic>? body, {
    Map<String, dynamic>? query,
    Map<String, dynamic>? headers,
  }) async* {
    final response = await dio.post<ResponseBody>(
      path,
      data: body,
      queryParameters: query,
      options: Options(
        responseType: ResponseType.stream,
        headers: {'Content-Type': 'application/json', ...?headers},
      ),
    );
    final bodyStream = response.data;
    if (bodyStream == null) throw const ApiException('服务器没有返回流式内容。');
    final lines = bodyStream.stream
        .cast<List<int>>()
        .transform(utf8.decoder)
        .transform(const LineSplitter());
    await for (final line in lines) {
      if (line.trim().isEmpty) continue;
      final event = jsonDecode(line) as Map<String, dynamic>;
      if (event['type'] == 'error') {
        throw ApiException(
          event['message'] as String? ?? '剧情生成失败。',
          code: event['code'] as String? ?? 'stream_failed',
          retryable: event['retryable'] == true,
        );
      }
      yield event;
    }
  }

  String mediaUrl(String value) {
    if (value.isEmpty ||
        value.startsWith('http://') ||
        value.startsWith('https://')) {
      return value;
    }
    final api = Uri.parse(AppConfig.apiBaseUrl);
    final origin =
        '${api.scheme}://${api.host}${api.hasPort ? ':${api.port}' : ''}';
    return '$origin/${value.replaceFirst(RegExp(r'^/+'), '')}';
  }
}
