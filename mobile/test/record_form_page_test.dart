import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:word_game_by_ai/core/ui/record_form_page.dart';

void main() {
  testWidgets('缺失的布尔字段默认关闭', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: RecordFormPage(
        title: '测试',
        fields: const [
          RecordField('clear_api_key', '清除密钥', type: RecordFieldType.boolean),
        ],
        onSave: (_) async {},
      ),
    ));

    expect(tester.widget<SwitchListTile>(find.byType(SwitchListTile)).value,
        isFalse);
  });

  testWidgets('无效选择值回退到第一个有效选项', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: RecordFormPage(
        title: '测试',
        fields: const [
          RecordField('role', '角色',
              type: RecordFieldType.choice,
              options: {'npc': 'NPC', 'protagonist': '主角'}),
        ],
        initial: const {'role': 'legacy-role'},
        onSave: (_) async {},
      ),
    ));

    final field = tester.widget<DropdownButtonFormField<String>>(
        find.byType(DropdownButtonFormField<String>));
    expect(field.initialValue, 'npc');
  });
}
