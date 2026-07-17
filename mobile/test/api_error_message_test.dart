import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:word_game_by_ai/core/network/api_client.dart';

void main() {
  test('显示服务器返回的中文错误，不暴露 Dio 异常', () {
    final request = RequestOptions(path: '/auth/login');
    final error = DioException.badResponse(
      statusCode: 401,
      requestOptions: request,
      response: Response<Map<String, dynamic>>(
        requestOptions: request,
        statusCode: 401,
        data: {'detail': '用户名或密码错误。'},
      ),
    );

    expect(apiErrorMessage(error), '用户名或密码错误。');
  });

  test('连接超时返回可理解的提示', () {
    final error = DioException.connectionTimeout(
      timeout: const Duration(seconds: 15),
      requestOptions: RequestOptions(path: '/auth/login'),
    );

    expect(apiErrorMessage(error), contains('连接服务器超时'));
  });
}
