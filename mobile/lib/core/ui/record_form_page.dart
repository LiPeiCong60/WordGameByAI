import 'package:flutter/material.dart';

import '../network/api_client.dart';

enum RecordFieldType { text, integer, decimal, boolean, choice, password }

class RecordField {
  const RecordField(
    this.key,
    this.label, {
    this.type = RecordFieldType.text,
    this.lines = 1,
    this.required = false,
    this.options = const {},
    this.helper,
    this.section,
  });

  final String key;
  final String label;
  final RecordFieldType type;
  final int lines;
  final bool required;
  final Map<String, String> options;
  final String? helper;
  final String? section;
}

class RecordFormPage extends StatefulWidget {
  const RecordFormPage({
    super.key,
    required this.title,
    required this.fields,
    required this.onSave,
    this.initial = const {},
    this.saveLabel = '保存',
    this.headerBuilder,
  });

  final String title;
  final List<RecordField> fields;
  final Map<String, dynamic> initial;
  final Future<void> Function(Map<String, dynamic>) onSave;
  final String saveLabel;
  final Widget Function(BuildContext context, Map<String, dynamic> values)?
      headerBuilder;

  @override
  State<RecordFormPage> createState() => _RecordFormPageState();
}

class _RecordFormPageState extends State<RecordFormPage> {
  final Map<String, TextEditingController> _controllers = {};
  final Map<String, bool> _booleans = {};
  final Map<String, String?> _choices = {};
  bool _saving = false;
  String _error = '';

  @override
  void initState() {
    super.initState();
    for (final field in widget.fields) {
      final value = widget.initial[field.key];
      if (field.type == RecordFieldType.boolean) {
        _booleans[field.key] =
            value is bool ? value : value?.toString().toLowerCase() == 'true';
      } else if (field.type == RecordFieldType.choice) {
        final candidate = value?.toString();
        _choices[field.key] = candidate != null &&
                candidate.isNotEmpty &&
                field.options.containsKey(candidate)
            ? candidate
            : field.options.keys.firstOrNull;
      } else {
        _controllers[field.key] =
            TextEditingController(text: value?.toString() ?? '');
      }
    }
  }

  Future<void> _save() async {
    final data = <String, dynamic>{};
    for (final field in widget.fields) {
      if (field.type == RecordFieldType.boolean) {
        data[field.key] = _booleans[field.key] ?? false;
      } else if (field.type == RecordFieldType.choice) {
        data[field.key] = _choices[field.key] ?? '';
      } else {
        final value = _controllers[field.key]!.text;
        if (field.required && value.trim().isEmpty) {
          setState(() => _error = '请填写${field.label}。');
          return;
        }
        if (field.type == RecordFieldType.integer) {
          data[field.key] = int.tryParse(value) ?? 0;
        } else if (field.type == RecordFieldType.decimal) {
          data[field.key] = double.tryParse(value) ?? 0;
        } else {
          data[field.key] = value.trim();
        }
      }
    }
    setState(() {
      _saving = true;
      _error = '';
    });
    try {
      await widget.onSave(data);
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (mounted) setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Map<String, dynamic> _currentValues() {
    final data = <String, dynamic>{};
    for (final field in widget.fields) {
      if (field.type == RecordFieldType.boolean) {
        data[field.key] = _booleans[field.key] ?? false;
      } else if (field.type == RecordFieldType.choice) {
        data[field.key] = _choices[field.key] ?? '';
      } else {
        final value = _controllers[field.key]?.text.trim() ?? '';
        data[field.key] = switch (field.type) {
          RecordFieldType.integer => int.tryParse(value) ?? 0,
          RecordFieldType.decimal => double.tryParse(value) ?? 0,
          _ => value,
        };
      }
    }
    return data;
  }

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(widget.title)),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
          children: [
            if (widget.headerBuilder != null) ...[
              widget.headerBuilder!(context, _currentValues()),
              const SizedBox(height: 22),
            ],
            for (final field in widget.fields) ...[
              if (field.section != null) ...[
                Padding(
                  padding: const EdgeInsets.fromLTRB(2, 6, 2, 10),
                  child: Text(
                    field.section!,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: Theme.of(context).colorScheme.primary,
                          fontWeight: FontWeight.w800,
                          letterSpacing: .3,
                        ),
                  ),
                ),
              ],
              if (field.type == RecordFieldType.boolean)
                SwitchListTile(
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                  title: Text(field.label),
                  subtitle: field.helper == null ? null : Text(field.helper!),
                  value: _booleans[field.key] ?? false,
                  onChanged: (value) =>
                      setState(() => _booleans[field.key] = value),
                )
              else if (field.type == RecordFieldType.choice)
                DropdownButtonFormField<String>(
                  initialValue: _choices[field.key],
                  decoration: InputDecoration(
                      labelText: field.label, helperText: field.helper),
                  items: field.options.entries
                      .map((item) => DropdownMenuItem(
                          value: item.key, child: Text(item.value)))
                      .toList(),
                  onChanged: (value) =>
                      setState(() => _choices[field.key] = value),
                )
              else
                TextField(
                  controller: _controllers[field.key],
                  maxLines: field.lines,
                  obscureText: field.type == RecordFieldType.password,
                  keyboardType: switch (field.type) {
                    RecordFieldType.integer => TextInputType.number,
                    RecordFieldType.decimal =>
                      const TextInputType.numberWithOptions(decimal: true),
                    _ => field.lines > 1
                        ? TextInputType.multiline
                        : TextInputType.text,
                  },
                  decoration: InputDecoration(
                      labelText: '${field.label}${field.required ? ' *' : ''}',
                      helperText: field.helper),
                  onChanged: widget.headerBuilder == null
                      ? null
                      : (_) => setState(() {}),
                ),
              const SizedBox(height: 12),
            ],
            if (_error.isNotEmpty)
              Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Text(_error,
                      style: TextStyle(
                          color: Theme.of(context).colorScheme.error))),
          ],
        ),
        bottomNavigationBar: SafeArea(
          top: false,
          child: Container(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              border: Border(
                top: BorderSide(
                    color: Theme.of(context).colorScheme.outlineVariant),
              ),
            ),
            child: FilledButton.icon(
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.save_outlined),
              label: Text(_saving ? '保存中…' : widget.saveLabel),
            ),
          ),
        ),
      );
}
