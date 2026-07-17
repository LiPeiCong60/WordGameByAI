import 'package:flutter_test/flutter_test.dart';
import 'package:word_game_by_ai/core/config/app_config.dart';

void main() {
  test('uses the Android emulator API endpoint by default', () {
    expect(AppConfig.apiBaseUrl, 'http://10.0.2.2:8000/api/v1');
  });

  test('does not duplicate the v1 API prefix', () {
    expect(AppConfig.v1Path('/games'), '/games');
    expect(
      AppConfig.v1Path('/games', baseUrl: 'https://example.com/api'),
      '/v1/games',
    );
  });
}
