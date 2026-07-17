# World Game by AI · Android

Flutter Android 客户端，当前版本 `0.4.0+4`。平台工程已经包含在仓库中，请勿再次运行 `flutter create` 覆盖现有 Android 配置。

## 已实现功能

- 算术验证码注册、登录、刷新令牌轮换和注销。
- Keystore/Keychain 安全令牌存储，401 自动刷新并重试。
- 存档创建、编辑、删除、JSON 导入与导出。
- 世界模板、世界/副本、世界观和完整角色卡管理。
- 12 类 AI 漫剧默认头像、标签自动匹配、上传/删除/恢复头像。
- AI 开场和回合推进，NDJSON 流式解析为旁白、动作、心理与角色对话。
- 极速、快速、精细三档生成模式。
- 历史回合游标分页、指定回合重生成和状态同步。
- 动态记忆 RAG 浏览、检索与重建。
- 管理 Agent 提案、确认与拒绝。
- 管理员用户、会员、额度、模型池、模型等级和用量管理。

## 运行

```bash
flutter pub get
flutter run \
  --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
```

`10.0.2.2` 是 Android 模拟器访问宿主机的地址。连接公网服务时应使用 HTTPS：

```bash
flutter run \
  --dart-define=API_BASE_URL=https://your-domain.example/api/v1
```

## 测试

```bash
flutter analyze
flutter test
```

## 构建测试 APK

```bash
flutter build apk --release \
  --dart-define=API_BASE_URL=https://your-domain.example/api/v1
```

当前 release 仍使用开发签名，`applicationId` 仍为 `com.example.word_game_by_ai`，开发 Manifest 也允许明文 HTTP 以兼容本地/IP 测试。应用商店发布前必须：

1. 换成唯一的正式 application ID。
2. 创建私有 release keystore，并仅通过本地 `key.properties` 或 CI Secret 提供凭据。
3. 强制 HTTPS，在 release Manifest 中禁止 cleartext traffic。
4. 配置版本策略、隐私政策、商店截图和签名备份。

完整项目说明见仓库根目录 [README](../README.md)。
