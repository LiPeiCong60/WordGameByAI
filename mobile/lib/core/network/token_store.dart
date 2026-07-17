import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenStore {
  static const _accessKey = 'wordgame_access_token';
  static const _refreshKey = 'wordgame_refresh_token';
  static const _userKey = 'wordgame_user';
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Future<String?> readAccessToken() => _storage.read(key: _accessKey);
  Future<String?> readRefreshToken() => _storage.read(key: _refreshKey);
  Future<Map<String, dynamic>?> readUser() async {
    final value = await _storage.read(key: _userKey);
    if (value == null || value.isEmpty) return null;
    try {
      return jsonDecode(value) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  Future<void> saveSession(Map<String, dynamic> session) async {
    await _storage.write(key: _accessKey, value: session['token'] as String?);
    await _storage.write(
        key: _refreshKey, value: session['refresh_token'] as String?);
    final user = session['user'];
    if (user is Map) {
      await _storage.write(key: _userKey, value: jsonEncode(user));
    }
  }

  Future<void> saveUser(Map<String, dynamic> user) async {
    await _storage.write(key: _userKey, value: jsonEncode(user));
  }

  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    await _storage.delete(key: _userKey);
  }
}
