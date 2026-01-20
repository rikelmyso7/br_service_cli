import pandas as pd
import os

def comparar_arquivos_excel(caminho_arquivo_gerado, caminho_arquivo_exemplo):
    """
    Compara o conteúdo de dois arquivos Excel (gerado e exemplo).
    Retorna True se o conteúdo for similar, False caso contrário.
    """
    try:
        print(f"\nComparando:\n  Gerado: {caminho_arquivo_gerado}\n  Exemplo: {caminho_arquivo_exemplo}")

        # Carregar o arquivo gerado (espera-se .xlsx)
        df_gerado = pd.read_excel(caminho_arquivo_gerado, engine='openpyxl')

        # Carregar o arquivo exemplo (pode ser .xls ou .xlsx)
        # Tenta openpyxl primeiro, depois xlrd para .xls antigos
        try:
            df_exemplo = pd.read_excel(caminho_arquivo_exemplo, engine='openpyxl')
        except Exception:
            df_exemplo = pd.read_excel(caminho_arquivo_exemplo, engine='xlrd')

        # Normalizar nomes de colunas (remover espaços, converter para minúsculas, etc.)
        df_gerado.columns = [col.strip().lower().replace(' ', '_') for col in df_gerado.columns]
        df_exemplo.columns = [col.strip().lower().replace(' ', '_') for col in df_exemplo.columns]

        # Verificar se as colunas são as mesmas
        if not set(df_gerado.columns) == set(df_exemplo.columns):
            print(f"Colunas diferentes:\n  Gerado: {df_gerado.columns}\n  Exemplo: {df_exemplo.columns}")
            return False

        # Ordenar os DataFrames para garantir a comparação linha a linha
        # Assumindo que 'contrato' é uma boa chave para ordenação
        if 'contrato' in df_gerado.columns:
            df_gerado = df_gerado.sort_values(by='contrato').reset_index(drop=True)
            df_exemplo = df_exemplo.sort_values(by='contrato').reset_index(drop=True)

        # Comparar o conteúdo dos DataFrames
        # Usar .equals() para comparação exata ou uma lógica mais flexível para valores numéricos/datas
        
        # Para uma comparação mais robusta, vamos iterar sobre as colunas e comparar tipo a tipo
        # e permitir uma pequena tolerância para floats.
        
        if len(df_gerado) != len(df_exemplo):
            print(f"Número de linhas diferente: Gerado={len(df_gerado)}, Exemplo={len(df_exemplo)}")
            return False

        for col in df_gerado.columns:
            if col not in df_exemplo.columns:
                print(f"Coluna {col} não encontrada no arquivo exemplo.")
                return False
            
            # Comparar valores
            for i in range(len(df_gerado)):
                val_gerado = df_gerado.loc[i, col]
                val_exemplo = df_exemplo.loc[i, col]

                if pd.isna(val_gerado) and pd.isna(val_exemplo):
                    continue
                if pd.isna(val_gerado) != pd.isna(val_exemplo):
                    print(f"Diferença de NaN na coluna {col}, linha {i}: Gerado={val_gerado}, Exemplo={val_exemplo}")
                    return False

                if isinstance(val_gerado, (int, float)) and isinstance(val_exemplo, (int, float)):
                    if not pd.isclose(val_gerado, val_exemplo, rel_tol=1e-2):
                        print(f"Diferença numérica na coluna {col}, linha {i}: Gerado={val_gerado}, Exemplo={val_exemplo}")
                        return False
                elif str(val_gerado).strip() != str(val_exemplo).strip():
                    print(f"Diferença de string na coluna {col}, linha {i}: Gerado=\"{val_gerado}\", Exemplo=\"{val_exemplo}\"")
                    return False

        print("Conteúdo dos arquivos é similar.")
        return True

    except Exception as e:
        print(f"Erro ao comparar arquivos Excel: {e}")
        return False

if __name__ == '__main__':
    # Exemplo de uso
    caminho_gerado = '/tmp/teste_saida/AZ/AZ-1.01.02.01.xlsx'
    caminho_exemplo = '/home/ubuntu/upload/AZ-1.01.02.01.xls'

    if comparar_arquivos_excel(caminho_gerado, caminho_exemplo):
        print("Comparação bem-sucedida!")
    else:
        print("Comparação falhou.")

    # Testar outros arquivos
    # ADTC
    caminho_gerado_adtc = '/tmp/teste_saida/ADTC/ADTC-1.04.01.07.xlsx'
    caminho_exemplo_adtc = '/home/ubuntu/upload/ADTC-1.04.01.07.xls'
    comparar_arquivos_excel(caminho_gerado_adtc, caminho_exemplo_adtc)

    # REG
    caminho_gerado_reg = '/tmp/teste_saida/REG/REG-1.04.01.08.xlsx'
    caminho_exemplo_reg = '/home/ubuntu/upload/REG-1.04.01.08.xls'
    comparar_arquivos_excel(caminho_gerado_reg, caminho_exemplo_reg)

    # EO
    caminho_gerado_eo = '/tmp/teste_saida/EO/EO-2.01.09.13.xlsx'
    caminho_exemplo_eo = '/home/ubuntu/upload/EO-2.01.09.13.xls'
    comparar_arquivos_excel(caminho_gerado_eo, caminho_exemplo_eo)

    # COND
    caminho_gerado_cond = '/tmp/teste_saida/COND/COND-2.01.09.17.xlsx'
    caminho_exemplo_cond = '/home/ubuntu/upload/COND-2.01.09.17.xls'
    comparar_arquivos_excel(caminho_gerado_cond, caminho_exemplo_cond)

    # TX
    caminho_gerado_tx = '/tmp/teste_saida/TX/TX-2.01.09.20.xlsx'
    caminho_exemplo_tx = '/home/ubuntu/upload/TX-2.01.09.20.xls'
    comparar_arquivos_excel(caminho_gerado_tx, caminho_exemplo_tx)

    # TTT
    caminho_gerado_ttt = '/tmp/teste_saida/TTT/TTT-1.04.01.19.xlsx'
    caminho_exemplo_ttt = '/home/ubuntu/upload/TTT-1.04.01.19.xls'
    comparar_arquivos_excel(caminho_gerado_ttt, caminho_exemplo_ttt)

    # ADTC (outro)
    # O arquivo ADTC-1.04.01.20.xlsx foi gerado, mas não há um exemplo correspondente com esse nome.
    # Vou usar o ADTC-1.04.01.07.xls para comparar, mas pode haver diferenças.
    # É importante notar que o sistema gerou 10 arquivos, mas só temos 7 exemplos.
    # Precisamos de clareza sobre quais arquivos de exemplo correspondem a quais saídas.
    # Por enquanto, vou comparar os que têm nomes semelhantes.
    # ADTC-1.04.01.20.xlsx vs ADTC-1.04.01.07.xls
    # caminho_gerado_adtc2 = '/tmp/teste_saida/ADTC/ADTC-1.04.01.20.xlsx'
    # caminho_exemplo_adtc_alt = '/home/ubuntu/upload/ADTC-1.04.01.07.xls'
    # comparar_arquivos_excel(caminho_gerado_adtc2, caminho_exemplo_adtc_alt)


