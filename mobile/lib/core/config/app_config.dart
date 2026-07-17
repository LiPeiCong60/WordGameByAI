class AppConfig {
  const AppConfig._();

  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );

  static String v1Path(String path, {String? baseUrl}) {
    final normalized = path.startsWith('/') ? path : '/$path';
    final basePath = Uri.parse(baseUrl ?? apiBaseUrl).path;
    return basePath.endsWith('/v1') ? normalized : '/v1$normalized';
  }
}
