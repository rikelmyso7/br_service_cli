```dart
import 'dart:convert';
import 'dart:io';
import 'package_name/models/br_service_models.dart'; // Mantenha seus modelos
import 'package:intl/intl.dart';

// #############################################################################
// EXCEÇÃO CUSTOMIZADA
// #############################################################################

class BRServiceException implements Exception {
  final String message;
  final int? exitCode;

  BRServiceException(this.message, {this.exitCode});

  @override
  String toString() {
    return 'BRServiceException (Exit Code: $exitCode): $message';
  }
}

// #############################################################################
// CLIENTE DE SERVIÇO (ADAPTADO PARA .EXE)
// #############################################################################

class BRServiceClient {
  /// O caminho completo para o seu executável compilado (ex: 'C:/path/to/cli.exe').
  final String executablePath;

  BRServiceClient({required this.executablePath}) {
    if (!File(executablePath).existsSync()) {
      throw ArgumentError.value(
          executablePath, 'executablePath', 'Arquivo executável não encontrado.');
    }
  }

  /// Busca as opções de documentos e datas do arquivo de entrada.
  Future<ProcessingOptions> getOptions(String inputFile) async {
    final arguments = [
      '--input',
      inputFile,
      '--get-options',
    ];

    final result = await _runProcess(arguments);
    final jsonResponse = jsonDecode(result.stdout);
    return ProcessingOptions.fromJson(jsonResponse);
  }

  /// Extrai os dados e os retorna em formato JSON sem gerar arquivos.
  Future<ExtractionResult> extractData({
    required String inputFile,
    List<String>? selectedDocuments,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final arguments = [
      '--input',
      inputFile,
      '--extract-only',
    ];

    _addOptionalArguments(arguments, selectedDocuments, startDate, endDate);

    final result = await _runProcess(arguments);
    final jsonResponse = jsonDecode(result.stdout);
    return ExtractionResult.fromJson(jsonResponse);
  }

  /// Processa os dados e gera os arquivos de saída .xls.
  Future<FileGenerationResult> processAndGenerateFiles({
    required String inputFile,
    required String outputDir,
    List<String>? selectedDocuments,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final arguments = [
      '--input',
      inputFile,
      '--output',
      outputDir,
    ];

    _addOptionalArguments(arguments, selectedDocuments, startDate, endDate);

    final result = await _runProcess(arguments);
    final jsonResponse = jsonDecode(result.stdout);
    return FileGenerationResult.fromJson(jsonResponse);
  }

  // --- Métodos Privados ---

  Future<ProcessResult> _runProcess(List<String> arguments) async {
    // A chamada agora é diretamente no executável.
    final result = await Process.run(executablePath, arguments);

    if (result.exitCode != 0) {
      throw BRServiceException(
        'Falha no processo: ${result.stderr}',
        exitCode: result.exitCode,
      );
    }
    if (result.stdout.toString().isEmpty) {
      throw BRServiceException(
        'O script não retornou nenhuma saída (stdout). Stderr: ${result.stderr}',
        exitCode: result.exitCode,
      );
    }
    return result;
  }

  void _addOptionalArguments(
    List<String> arguments,
    List<String>? selectedDocuments,
    DateTime? startDate,
    DateTime? endDate,
  ) {
    if (selectedDocuments != null && selectedDocuments.isNotEmpty) {
      arguments.addAll(['--documentos', selectedDocuments.join(',')]);
    }
    if (startDate != null) {
      arguments.addAll(['--data-inicio', _formatDate(startDate)]);
    }
    if (endDate != null) {
      arguments.addAll(['--data-fim', _formatDate(endDate)]);
    }
  }

  String _formatDate(DateTime date) {
    return DateFormat('dd/MM/yyyy').format(date);
  }
}

/*
--------------------------------------------------------------------------------
LEMBRETE: OS MODELOS DE DADOS NÃO MUDAM!

Os modelos (ProcessingOptions, ExtractionResult, etc.) que você criou para 
decodificar o JSON permanecem exatamente os mesmos, pois a saída do seu 
script Python não foi alterada.

Crie um arquivo para os modelos, por exemplo: lib/models/br_service_models.dart

class ProcessingOptions { ... }
class DocumentOption { ... }
class ExtractionResult { ... }
class FileGenerationResult { ... }
--------------------------------------------------------------------------------
*/
```
