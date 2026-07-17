import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../core/network/api_client.dart';
import '../../core/network/token_store.dart';

class RegisterPage extends StatefulWidget {
  const RegisterPage({
    super.key,
    required this.api,
    required this.tokenStore,
    required this.onAuthenticated,
    required this.onShowLogin,
  });

  final ApiClient api;
  final TokenStore tokenStore;
  final VoidCallback onAuthenticated;
  final VoidCallback onShowLogin;

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final _username = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirmPassword = TextEditingController();
  final _bootstrapToken = TextEditingController();
  final _captchaAnswer = TextEditingController();
  final _usernameFocus = FocusNode();
  final _emailFocus = FocusNode();
  final _passwordFocus = FocusNode();
  final _confirmPasswordFocus = FocusNode();
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

  Future<void> _loadCaptcha({bool clearError = true}) async {
    try {
      final data = await widget.api.getJson('/auth/captcha');
      if (!mounted) return;
      setState(() {
        _captchaId = data['captcha_id'] as String? ?? '';
        _captchaSvg = data['svg'] as String? ?? '';
        _captchaAnswer.clear();
        if (clearError) _error = '';
      });
    } catch (error) {
      if (mounted) setState(() => _error = '验证码加载失败：${apiErrorMessage(error)}');
    }
  }

  String? _validate() {
    final username = _username.text.trim();
    if (username.length < 3 || username.length > 32) {
      return '用户名长度需要在 3 到 32 个字符之间。';
    }
    if (!RegExp(r'^[\p{L}\p{N}_-]+$', unicode: true).hasMatch(username)) {
      return '用户名只能包含字母、数字、下划线和短横线。';
    }
    if (_password.text.length < 8) return '密码至少需要 8 位。';
    if (_password.text != _confirmPassword.text) return '两次输入的密码不一致。';
    if (_captchaId.isEmpty || _captchaAnswer.text.trim().isEmpty) {
      return '请填写验证码。';
    }
    return null;
  }

  Future<void> _register() async {
    final validationError = _validate();
    if (validationError != null) {
      setState(() => _error = validationError);
      return;
    }
    setState(() {
      _loading = true;
      _error = '';
    });
    try {
      final session = await widget.api.postJson('/auth/register', {
        'username': _username.text.trim(),
        'email': _email.text.trim(),
        'password': _password.text,
        'bootstrap_token': _bootstrapToken.text.trim(),
        'captcha_id': _captchaId,
        'captcha_answer': _captchaAnswer.text.trim(),
      });
      await widget.tokenStore.saveSession(session);
      widget.onAuthenticated();
    } catch (error) {
      if (mounted) setState(() => _error = apiErrorMessage(error));
      await _loadCaptcha(clearError: false);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _username.dispose();
    _email.dispose();
    _password.dispose();
    _confirmPassword.dispose();
    _bootstrapToken.dispose();
    _captchaAnswer.dispose();
    _usernameFocus.dispose();
    _emailFocus.dispose();
    _passwordFocus.dispose();
    _confirmPasswordFocus.dispose();
    _captchaFocus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
            onPressed: widget.onShowLogin, icon: const Icon(Icons.arrow_back)),
        title: const Text('注册账号'),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: AutofillGroup(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(18),
                        child: Image.asset('assets/brand/app_icon.png',
                            width: 64, height: 64),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('创建你的世界通行证',
                                style: Theme.of(context)
                                    .textTheme
                                    .titleLarge
                                    ?.copyWith(fontWeight: FontWeight.w800)),
                            const SizedBox(height: 3),
                            Text('存档与角色会安全同步到服务器',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(
                                        color: Theme.of(context)
                                            .colorScheme
                                            .onSurfaceVariant)),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _username,
                    focusNode: _usernameFocus,
                    autofillHints: const [AutofillHints.newUsername],
                    textInputAction: TextInputAction.next,
                    onSubmitted: (_) => _emailFocus.requestFocus(),
                    decoration: const InputDecoration(
                        labelText: '用户名', helperText: '3–32 位，可使用字母、数字、_ 和 -'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _email,
                    focusNode: _emailFocus,
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.email],
                    textInputAction: TextInputAction.next,
                    onSubmitted: (_) => _passwordFocus.requestFocus(),
                    decoration: const InputDecoration(labelText: '邮箱（可选）'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _password,
                    focusNode: _passwordFocus,
                    obscureText: _obscurePassword,
                    autofillHints: const [AutofillHints.newPassword],
                    textInputAction: TextInputAction.next,
                    onSubmitted: (_) => _confirmPasswordFocus.requestFocus(),
                    decoration: InputDecoration(
                      labelText: '密码',
                      helperText: '至少 8 位',
                      suffixIcon: IconButton(
                        onPressed: () => setState(
                            () => _obscurePassword = !_obscurePassword),
                        icon: Icon(_obscurePassword
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _confirmPassword,
                    focusNode: _confirmPasswordFocus,
                    obscureText: _obscurePassword,
                    textInputAction: TextInputAction.next,
                    onSubmitted: (_) => _captchaFocus.requestFocus(),
                    decoration: const InputDecoration(labelText: '再次输入密码'),
                  ),
                  const SizedBox(height: 12),
                  ExpansionTile(
                    tilePadding: EdgeInsets.zero,
                    title: const Text('初始管理员令牌（普通用户无需填写）'),
                    children: [
                      TextField(
                        controller: _bootstrapToken,
                        obscureText: true,
                        decoration: const InputDecoration(labelText: '管理员令牌'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  if (_captchaSvg.isNotEmpty)
                    Semantics(
                      button: true,
                      label: '点击刷新验证码',
                      child: InkWell(
                        onTap: _loading ? null : _loadCaptcha,
                        child: SizedBox(
                            height: 64, child: SvgPicture.string(_captchaSvg)),
                      ),
                    ),
                  TextField(
                    controller: _captchaAnswer,
                    focusNode: _captchaFocus,
                    keyboardType: TextInputType.number,
                    textInputAction: TextInputAction.done,
                    decoration: const InputDecoration(labelText: '验证码'),
                    onSubmitted: _loading ? null : (_) => _register(),
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
                    onPressed: _loading ? null : _register,
                    child: Text(_loading ? '注册中…' : '注册并登录'),
                  ),
                  const SizedBox(height: 8),
                  TextButton(
                      onPressed: _loading ? null : widget.onShowLogin,
                      child: const Text('已有账号？返回登录')),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
