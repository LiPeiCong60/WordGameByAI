import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../core/network/api_client.dart';
import '../../core/network/token_store.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({
    super.key,
    required this.api,
    required this.tokenStore,
    required this.onAuthenticated,
    required this.onShowRegister,
  });

  final ApiClient api;
  final TokenStore tokenStore;
  final VoidCallback onAuthenticated;
  final VoidCallback onShowRegister;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _username = TextEditingController();
  final _password = TextEditingController();
  final _captchaAnswer = TextEditingController();
  final _usernameFocus = FocusNode();
  final _passwordFocus = FocusNode();
  final _captchaFocus = FocusNode();
  String _captchaId = '';
  String _captchaSvg = '';
  String _error = '';
  bool _loading = false;
  bool _obscurePassword = true;

  @override
  void initState() {
    super.initState();
    _loadCaptcha();
  }

  Future<void> _loadCaptcha() async {
    try {
      final data = await widget.api.getJson('/auth/captcha');
      if (!mounted) return;
      setState(() {
        _captchaId = data['captcha_id'] as String? ?? '';
        _captchaSvg = data['svg'] as String? ?? '';
        _captchaAnswer.clear();
      });
    } catch (error) {
      if (mounted) {
        setState(() => _error = '验证码加载失败：${apiErrorMessage(error)}');
      }
    }
  }

  Future<void> _login() async {
    if (_username.text.trim().isEmpty ||
        _password.text.isEmpty ||
        _captchaAnswer.text.trim().isEmpty) {
      setState(() => _error = '请填写用户名、密码和验证码。');
      return;
    }
    setState(() {
      _loading = true;
      _error = '';
    });
    try {
      final session = await widget.api.postJson('/auth/login', {
        'username': _username.text.trim(),
        'password': _password.text,
        'captcha_id': _captchaId,
        'captcha_answer': _captchaAnswer.text.trim(),
      });
      await widget.tokenStore.saveSession(session);
      widget.onAuthenticated();
    } catch (error) {
      if (mounted) setState(() => _error = apiErrorMessage(error));
      await _loadCaptcha();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _username.dispose();
    _password.dispose();
    _captchaAnswer.dispose();
    _usernameFocus.dispose();
    _passwordFocus.dispose();
    _captchaFocus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(9),
              child: Image.asset('assets/brand/app_icon.png',
                  width: 34, height: 34),
            ),
            const SizedBox(width: 10),
            const Text('World Game by AI'),
          ],
        ),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('继续你的故事',
                    textAlign: TextAlign.center,
                    style: Theme.of(context)
                        .textTheme
                        .headlineMedium
                        ?.copyWith(fontWeight: FontWeight.w800)),
                const SizedBox(height: 6),
                Text(
                  '登录后同步角色、世界设定与每一回剧情',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant),
                ),
                const SizedBox(height: 26),
                TextField(
                    controller: _username,
                    focusNode: _usernameFocus,
                    textInputAction: TextInputAction.next,
                    autofillHints: const [AutofillHints.username],
                    onSubmitted: (_) => _passwordFocus.requestFocus(),
                    decoration: const InputDecoration(labelText: '用户名')),
                const SizedBox(height: 12),
                TextField(
                  controller: _password,
                  focusNode: _passwordFocus,
                  obscureText: _obscurePassword,
                  textInputAction: TextInputAction.next,
                  autofillHints: const [AutofillHints.password],
                  onSubmitted: (_) => _captchaFocus.requestFocus(),
                  decoration: InputDecoration(
                    labelText: '密码',
                    suffixIcon: IconButton(
                      onPressed: () =>
                          setState(() => _obscurePassword = !_obscurePassword),
                      icon: Icon(_obscurePassword
                          ? Icons.visibility_outlined
                          : Icons.visibility_off_outlined),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                if (_captchaSvg.isNotEmpty)
                  Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.fromLTRB(14, 6, 8, 6),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                          color: Theme.of(context).colorScheme.outlineVariant),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                            child: SizedBox(
                                height: 52,
                                child: SvgPicture.string(_captchaSvg))),
                        IconButton(
                          onPressed: _loading ? null : _loadCaptcha,
                          tooltip: '刷新验证码',
                          icon: const Icon(Icons.refresh),
                        ),
                      ],
                    ),
                  ),
                TextField(
                  controller: _captchaAnswer,
                  focusNode: _captchaFocus,
                  keyboardType: TextInputType.number,
                  textInputAction: TextInputAction.done,
                  decoration: const InputDecoration(labelText: '验证码'),
                  onSubmitted: _loading ? null : (_) => _login(),
                ),
                if (_error.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Text(_error,
                        style: TextStyle(
                            color: Theme.of(context).colorScheme.error)),
                  ),
                const SizedBox(height: 20),
                FilledButton(
                    onPressed: _loading ? null : _login,
                    child: Text(_loading ? '登录中…' : '登录')),
                const SizedBox(height: 8),
                TextButton(
                  onPressed: _loading ? null : widget.onShowRegister,
                  child: const Text('没有账号？注册新账号'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
