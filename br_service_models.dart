/// Este arquivo contém os modelos de dados para interagir com a API do BRService.

// #############################################################################
// MODELOS PARA --get-options
// #############################################################################

/// Representa a resposta completa ao solicitar opções de processamento.
class ProcessingOptions {
  final List<DocumentOption> documentOptions;

  ProcessingOptions({required this.documentOptions});

  /// Decodifica a resposta JSON do script.
  factory ProcessingOptions.fromJson(Map<String, dynamic> json) {
    // Navega pela estrutura JSON para encontrar a lista de documentos.
    final data = json['dados']?['opcoes']?['opcoes_documentos'] as List?;
    if (data == null) {
      throw FormatException(
          'Formato de resposta inválido: campo \'opcoes_documentos\' não encontrado.');
    }

    return ProcessingOptions(
      documentOptions: data
          .map((item) => DocumentOption.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// Representa um único documento com sua lista de datas disponíveis.
class DocumentOption {
  final String document;
  final List<String> dates;

  DocumentOption({required this.document, required this.dates});

  factory DocumentOption.fromJson(Map<String, dynamic> json) {
    final datesList = (json['datas'] as List?)?.map((e) => e.toString()).toList() ?? [];
    return DocumentOption(
      document: json['documento'] as String,
      dates: datesList,
    );
  }
}

// #############################################################################
// MODELO PARA --extract-only
// #############################################################################

/// Representa o resultado da extração de dados.
class ExtractionResult {
  /// Um mapa onde a chave é o nome do documento e o valor é uma lista de registros.
  final Map<String, List<Map<String, dynamic>>> extractedData;

  ExtractionResult({required this.extractedData});

  factory ExtractionResult.fromJson(Map<String, dynamic> json) {
    final data = json['dados']?['dados_extraidos'] as Map<String, dynamic>?;
    if (data == null) {
      throw FormatException(
          'Formato de resposta inválido: campo \'dados_extraidos\' não encontrado.');
    }

    // Garante que o mapa interno e as listas sejam do tipo correto.
    final castedData = data.map((key, value) {
      final records = (value as List)
          .map((record) => record as Map<String, dynamic>)
          .toList();
      return MapEntry(key, records);
    });

    return ExtractionResult(extractedData: castedData);
  }
}

// #############################################################################
// MODELO PARA GERAÇÃO DE ARQUIVOS
// #############################################################################

/// Representa o resultado da operação de geração de arquivos.
class FileGenerationResult {
  final List<String> generatedFiles;

  FileGenerationResult({required this.generatedFiles});

  factory FileGenerationResult.fromJson(Map<String, dynamic> json) {
    final files = (json['dados']?['arquivos_gerados'] as List?)
            ?.map((e) => e.toString())
            .toList() ??
        [];
    return FileGenerationResult(generatedFiles: files);
  }
}
