import 'package:flutter/material.dart';

import 'core/network/api_client.dart';
import 'core/network/token_store.dart';
import 'features/auth/login_page.dart';
import 'features/auth/register_page.dart';
import 'features/games/game_list_page.dart';

class WordGameApp extends StatefulWidget {
  const WordGameApp({super.key});

  @override
  State<WordGameApp> createState() => _WordGameAppState();
}

class _WordGameAppState extends State<WordGameApp> {
  final TokenStore _tokenStore = TokenStore();
  late final ApiClient _api = ApiClient(_tokenStore);
  bool _authenticated = false;
  bool _checkingSession = true;
  bool _showRegister = false;
  Map<String, dynamic>? _user;

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  Future<void> _restoreSession() async {
    final token = await _tokenStore.readAccessToken();
    if (token != null && token.isNotEmpty) {
      try {
        _user = await _api.getJson('/auth/me');
        await _tokenStore.saveUser(_user!);
        _authenticated = true;
      } catch (_) {
        await _tokenStore.clear();
      }
    }
    if (mounted) setState(() => _checkingSession = false);
  }

  Future<void> _logout() async {
    try {
      final refreshToken = await _tokenStore.readRefreshToken();
      await _api
          .postJson('/auth/logout', {'refresh_token': refreshToken ?? ''});
    } catch (_) {
      // A local logout must work even if the server is unreachable.
    }
    await _tokenStore.clear();
    if (mounted) {
      setState(() {
        _authenticated = false;
        _user = null;
      });
    }
  }

  Future<void> _authenticatedNow() async {
    try {
      _user = await _api.getJson('/auth/me');
      await _tokenStore.saveUser(_user!);
    } catch (_) {
      _user = await _tokenStore.readUser();
    }
    if (mounted) {
      setState(() {
        _authenticated = true;
        _showRegister = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF1677FF),
      brightness: Brightness.light,
    ).copyWith(
      surface: const Color(0xFFF8FBFF),
      surfaceContainerLowest: Colors.white,
      surfaceContainerLow: const Color(0xFFF1F7FF),
      surfaceContainer: const Color(0xFFE9F3FF),
      outline: const Color(0xFF747784),
      outlineVariant: const Color(0xFFD9E4F2),
    );
    return MaterialApp(
      title: 'World Game by AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: colorScheme,
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF5F9FF),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFFF8FBFF),
          surfaceTintColor: Colors.transparent,
          scrolledUnderElevation: 0,
          centerTitle: false,
          titleTextStyle: TextStyle(
            color: Color(0xFF172033),
            fontSize: 21,
            fontWeight: FontWeight.w700,
            letterSpacing: -.2,
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide(color: colorScheme.outlineVariant),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide(color: colorScheme.outlineVariant),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide(color: colorScheme.primary, width: 1.6),
          ),
        ),
        cardTheme: CardThemeData(
          margin: EdgeInsets.zero,
          elevation: 0,
          color: Colors.white,
          surfaceTintColor: Colors.transparent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
            side: BorderSide(color: colorScheme.outlineVariant),
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            minimumSize: const Size(48, 48),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
        ),
        navigationBarTheme: NavigationBarThemeData(
          height: 68,
          elevation: 0,
          backgroundColor: Colors.white,
          surfaceTintColor: Colors.transparent,
          indicatorColor: colorScheme.primaryContainer,
          iconTheme: WidgetStateProperty.resolveWith((states) => IconThemeData(
                size: states.contains(WidgetState.selected) ? 24 : 23,
                color: states.contains(WidgetState.selected)
                    ? colorScheme.onPrimaryContainer
                    : colorScheme.onSurfaceVariant,
              )),
        ),
        snackBarTheme: const SnackBarThemeData(
          behavior: SnackBarBehavior.floating,
          showCloseIcon: true,
        ),
      ),
      home: _checkingSession
          ? Scaffold(
              body: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(24),
                      child: Image.asset('assets/brand/app_icon.png',
                          width: 92, height: 92),
                    ),
                    const SizedBox(height: 22),
                    const SizedBox.square(
                      dimension: 24,
                      child: CircularProgressIndicator(strokeWidth: 2.4),
                    ),
                  ],
                ),
              ),
            )
          : _authenticated
              ? GameListPage(
                  api: _api, user: _user ?? const {}, onLogout: _logout)
              : _showRegister
                  ? RegisterPage(
                      api: _api,
                      tokenStore: _tokenStore,
                      onAuthenticated: _authenticatedNow,
                      onShowLogin: () => setState(() => _showRegister = false),
                    )
                  : LoginPage(
                      api: _api,
                      tokenStore: _tokenStore,
                      onAuthenticated: _authenticatedNow,
                      onShowRegister: () =>
                          setState(() => _showRegister = true),
                    ),
    );
  }
}
