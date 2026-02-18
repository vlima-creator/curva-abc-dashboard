"""
Processador de dados do Mercado Livre.
Mantém a lógica original de transformação do app.py.
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional
from .base_processor import BaseProcessor


class MercadoLivreProcessor(BaseProcessor):
    """Processador para relatórios do Mercado Livre."""
    
    def __init__(self):
        super().__init__()
        self.canal_name = "Mercado Livre"
    
    def detect(self, file) -> bool:
        """
        Detecta se o arquivo é um relatório do Mercado Livre.
        """
        try:
            file.seek(0)
            preview = pd.read_excel(file, sheet_name=0, header=None, nrows=80)
            file.seek(0)
            
            # Procura por colunas características do ML
            for i in range(min(60, len(preview))):
                row = preview.iloc[i].astype(str).str.lower()
                if row.str.contains('data da venda', na=False).any() or \
                   row.str.contains('# de anúncio', na=False).any() or \
                   row.str.contains('de anúncio', na=False).any():
                    return True
            
            return False
            
        except Exception:
            return False
    
    def process(self, files: list) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        Processa relatório do Mercado Livre.
        Mantém a lógica original do _transform_ml_raw.
        """
        if len(files) == 0:
            raise ValueError("Nenhum arquivo fornecido")
        
        # ML usa apenas um arquivo
        file = files[0]
        
        return self._transform_ml_raw(file)
    
    def _transform_ml_raw(self, file) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Converte o relatório bruto de vendas do Mercado Livre (120 dias) na estrutura 'Export'.
        Retorna: (df_export, df_logistics, df_ads)
        
        NOTA: Esta é a função original do app.py, mantida intacta.
        """
        
        def _seek0(f):
            try:
                f.seek(0)
            except Exception:
                pass
        
        def _pick_col(cols, target: str) -> str:
            if target in cols:
                return target
            for c in cols:
                sc = str(c).strip()
                if sc.startswith(target + "."):
                    return c
            t = target.lower()
            for c in cols:
                if t in str(c).lower():
                    return c
            raise KeyError(f"Coluna '{target}' não encontrada")
        
        def _try_pick_col(cols, target: str):
            try:
                return _pick_col(cols, target)
            except KeyError:
                return None
        
        _seek0(file)
        preview = pd.read_excel(file, sheet_name=0, header=None, nrows=80)
        
        header_row = None
        for i in range(min(60, len(preview))):
            row = preview.iloc[i].astype(str).str.lower()
            if row.str.contains('data da venda', na=False).any() or \
               row.str.contains('# de anúncio', na=False).any() or \
               row.str.contains('de anúncio', na=False).any():
                header_row = i
                break
        if header_row is None:
            header_row = 0
        
        _seek0(file)
        df = pd.read_excel(file, sheet_name=0, header=header_row)
        df.columns = [str(c).strip() for c in df.columns]
        
        col_data = _pick_col(df.columns, 'Data da venda')
        col_unid = _pick_col(df.columns, 'Unidades')
        
        try:
            col_rec = _pick_col(df.columns, 'Receita por produtos (BRL)')
        except Exception:
            col_rec = _pick_col(df.columns, 'Receita por produtos')
        
        col_mlb = _pick_col(df.columns, '# de anúncio')
        col_sku = _try_pick_col(df.columns, 'SKU')
        col_tit = _pick_col(df.columns, 'Título do anúncio')
        col_log = _pick_col(df.columns, 'Forma de entrega')
        
        # Nova coluna: Venda por publicidade
        col_ads = None
        ads_variations = [
            'Venda por publicidade',
            'Venda por Publicidade',
            'Vendas por Publicidade',
            'Vendas por publicidade',
            'vendas por publicidade',
            'venda por publicidade',
            'Publicidade',
            'publicidade',
        ]
        for var in ads_variations:
            col_ads = _try_pick_col(df.columns, var)
            if col_ads is not None:
                break
        
        if col_ads is None:
            for c in df.columns:
                c_lower = str(c).lower().strip()
                if 'publicidade' in c_lower:
                    col_ads = c
                    break
        
        use_cols = [col_data, col_unid, col_rec, col_mlb, col_tit, col_log]
        if col_sku is not None:
            use_cols.insert(4, col_sku)
        if col_ads is not None:
            use_cols.append(col_ads)
        
        base = df[use_cols].copy()
        
        # Renomear colunas
        if col_sku is None and col_ads is None:
            base.columns = ['data', 'unidades', 'receita', 'mlb', 'titulo', 'logistica']
            base['sku'] = ''
            base['ads'] = ''
        elif col_sku is None and col_ads is not None:
            base.columns = ['data', 'unidades', 'receita', 'mlb', 'titulo', 'logistica', 'ads']
            base['sku'] = ''
        elif col_sku is not None and col_ads is None:
            base.columns = ['data', 'unidades', 'receita', 'mlb', 'sku', 'titulo', 'logistica']
            base['ads'] = ''
        else:
            base.columns = ['data', 'unidades', 'receita', 'mlb', 'sku', 'titulo', 'logistica', 'ads']
        
        base['mlb'] = base['mlb'].astype(str).str.strip()
        base['sku'] = base['sku'].astype(str).str.strip()
        base['titulo'] = base['titulo'].astype(str).str.strip()
        base['logistica'] = base['logistica'].astype(str).str.strip()
        base['ads'] = base['ads'].astype(str).str.strip().str.lower()
        
        empty_mlb = base['mlb'].isin(['', 'nan', 'none', 'None', 'NaN'])
        if empty_mlb.any():
            base.loc[empty_mlb, 'mlb'] = base.loc[empty_mlb, 'sku']
        
        base['_data_raw'] = base['data'].astype(str)
        base['data'] = pd.to_datetime(base['_data_raw'], errors='coerce', dayfirst=True)
        
        if base['data'].notna().sum() == 0:
            s = base['_data_raw'].astype(str)
            for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y'):
                tmp = pd.to_datetime(s, errors='coerce', format=fmt)
                if tmp.notna().sum() > 0:
                    base['data'] = tmp
                    break
        
        if base['data'].notna().sum() == 0:
            month_map = {
                'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03',
                'abril': '04', 'maio': '05', 'junho': '06', 'julho': '07',
                'agosto': '08', 'setembro': '09', 'outubro': '10',
                'novembro': '11', 'dezembro': '12',
            }
            s = base['_data_raw'].astype(str).str.lower()
            s = s.str.replace('hs.', '', regex=False).str.replace('hs', '', regex=False)
            for name, num in month_map.items():
                s = s.str.replace(rf'\b{name}\b', num, regex=True)
            s = s.str.replace(r'\s*de\s*', '/', regex=True)
            s = s.str.replace(r'\s+', ' ', regex=True).str.strip()
            tmp = pd.to_datetime(s, errors='coerce', dayfirst=True)
            if tmp.notna().sum() > 0:
                base['data'] = tmp
        
        base = base.drop(columns=['_data_raw'], errors='ignore')
        base = base.dropna(subset=['data'])
        base = base[~base['mlb'].isin(['', 'nan', 'none', 'None', 'NaN'])].copy()
        
        base['unidades'] = pd.to_numeric(base['unidades'], errors='coerce').fillna(0).astype(int)
        
        rec = base['receita']
        if rec.dtype == object:
            rec = rec.astype(str).str.replace('\u00a0', '', regex=False).str.strip()
            # Se contiver tanto '.' quanto ',', assume formato BR (1.234,56)
            if rec.str.contains(r'\.', regex=True).any() and rec.str.contains(r',', regex=True).any():
                rec = rec.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            # Se contiver apenas ',', assume que é o separador decimal (1234,56)
            elif rec.str.contains(r',', regex=True).any():
                rec = rec.str.replace(',', '.', regex=False)
            # Remove símbolos de moeda se existirem
            rec = rec.str.replace(r'[R\$\s]', '', regex=True)
            
        base['receita'] = pd.to_numeric(rec, errors='coerce').fillna(0.0)
        
        if base.empty:
            cols = ['MLB','Título'] + [f'Qntd {p}' for p in ['0-30','31-60','61-90','91-120']] + \
                   [f'Fat. {p}' for p in ['0-30','31-60','61-90','91-120']] + \
                   [f'Curva {p}' for p in ['0-30','31-60','61-90','91-120']]
            empty_df = pd.DataFrame(columns=cols)
            empty_log = pd.DataFrame(columns=['periodo', 'full_pct', 'correios_pct', 'flex_pct', 'outros_pct', 
                                              'full_qty', 'correios_qty', 'flex_qty', 'outros_qty',
                                              'full_fat', 'correios_fat', 'flex_fat', 'outros_fat'])
            empty_ads = pd.DataFrame(columns=['periodo', 'ads_pct', 'organic_pct', 'ads_qty', 'organic_qty'])
            return empty_df, empty_log, empty_ads
        
        ref = base['data'].max()
        base['dias'] = (ref - base['data']).dt.days
        
        def bucket(d):
            if d <= 30:
                return '0-30'
            if d <= 60:
                return '31-60'
            if d <= 90:
                return '61-90'
            if d <= 120:
                return '91-120'
            return None
        
        base['periodo'] = base['dias'].apply(bucket)
        base = base.dropna(subset=['periodo'])
        
        # Classificar logística
        log_lower = base['logistica'].str.lower()
        base['is_full'] = log_lower.str.contains('full', na=False)
        base['is_correios'] = log_lower.str.contains('correios', na=False) | \
                              log_lower.str.contains('pontos', na=False) | \
                              log_lower.str.contains('ponto de envio', na=False)
        base['is_flex'] = log_lower.str.contains('flex', na=False)
        base['is_outros'] = ~(base['is_full'] | base['is_correios'] | base['is_flex'])
        
        # Classificar vendas por publicidade
        base['is_ads'] = base['ads'].str.lower().isin(['sim', 's', 'yes', 'y'])
        base['is_organic'] = ~base['is_ads']
        
        # Agregação por MLB e período
        agg = base.groupby(['mlb', 'titulo', 'periodo']).agg({
            'unidades': 'sum',
            'receita': 'sum'
        }).reset_index()
        
        # Pivot para ter colunas por período
        piv_qty = agg.pivot_table(index=['mlb', 'titulo'], columns='periodo', values='unidades', fill_value=0).reset_index()
        piv_rev = agg.pivot_table(index=['mlb', 'titulo'], columns='periodo', values='receita', fill_value=0.0).reset_index()
        
        # Renomear colunas
        for p in ['0-30', '31-60', '61-90', '91-120']:
            if p not in piv_qty.columns:
                piv_qty[p] = 0
            if p not in piv_rev.columns:
                piv_rev[p] = 0.0
        
        piv_qty = piv_qty.rename(columns={p: f'Qntd {p}' for p in ['0-30', '31-60', '61-90', '91-120']})
        piv_rev = piv_rev.rename(columns={p: f'Fat. {p}' for p in ['0-30', '31-60', '61-90', '91-120']})
        
        # Merge
        export = piv_qty.merge(piv_rev, on=['mlb', 'titulo'], how='outer')
        export = export.rename(columns={'mlb': 'MLB', 'titulo': 'Título'})
        
        # Calcula curva ABC para cada período
        for p in ['0-30', '31-60', '61-90', '91-120']:
            fat_col = f'Fat. {p}'
            curva_col = f'Curva {p}'
            
            # Ordena por faturamento
            export_sorted = export.sort_values(fat_col, ascending=False).copy()
            total_fat = export_sorted[fat_col].sum()
            
            if total_fat > 0:
                export_sorted['_pct_acum'] = (export_sorted[fat_col].cumsum() / total_fat) * 100
                
                def classify(pct):
                    if pct <= 80:
                        return 'A'
                    elif pct <= 95:
                        return 'B'
                    else:
                        return 'C'
                
                export_sorted[curva_col] = export_sorted['_pct_acum'].apply(classify)
                export_sorted.loc[export_sorted[fat_col] == 0, curva_col] = '-'
                
                # Merge de volta
                export = export.merge(export_sorted[['MLB', curva_col]], on='MLB', how='left', suffixes=('', '_new'))
                if curva_col + '_new' in export.columns:
                    export[curva_col] = export[curva_col + '_new']
                    export = export.drop(columns=[curva_col + '_new'])
            else:
                export[curva_col] = '-'
        
        # Métricas logísticas por período
        log_rows = []
        for p in ['0-30', '31-60', '61-90', '91-120']:
            base_p = base[base['periodo'] == p]
            total = len(base_p)
            
            if total > 0:
                full_qty = base_p['is_full'].sum()
                correios_qty = base_p['is_correios'].sum()
                flex_qty = base_p['is_flex'].sum()
                outros_qty = base_p['is_outros'].sum()
                
                full_fat = base_p[base_p['is_full']]['receita'].sum()
                correios_fat = base_p[base_p['is_correios']]['receita'].sum()
                flex_fat = base_p[base_p['is_flex']]['receita'].sum()
                outros_fat = base_p[base_p['is_outros']]['receita'].sum()
                
                log_rows.append({
                    'periodo': p,
                    'full_pct': full_qty / total,
                    'correios_pct': correios_qty / total,
                    'flex_pct': flex_qty / total,
                    'outros_pct': outros_qty / total,
                    'full_qty': int(full_qty),
                    'correios_qty': int(correios_qty),
                    'flex_qty': int(flex_qty),
                    'outros_qty': int(outros_qty),
                    'full_fat': float(full_fat),
                    'correios_fat': float(correios_fat),
                    'flex_fat': float(flex_fat),
                    'outros_fat': float(outros_fat)
                })
            else:
                log_rows.append({
                    'periodo': p,
                    'full_pct': 0, 'correios_pct': 0, 'flex_pct': 0, 'outros_pct': 0,
                    'full_qty': 0, 'correios_qty': 0, 'flex_qty': 0, 'outros_qty': 0,
                    'full_fat': 0.0, 'correios_fat': 0.0, 'flex_fat': 0.0, 'outros_fat': 0.0
                })
        
        df_logistics = pd.DataFrame(log_rows)
        
        # Métricas de Ads por período
        ads_rows = []
        for p in ['0-30', '31-60', '61-90', '91-120']:
            base_p = base[base['periodo'] == p]
            total = len(base_p)
            
            if total > 0:
                ads_qty = base_p['is_ads'].sum()
                organic_qty = base_p['is_organic'].sum()
                
                ads_value = base_p[base_p['is_ads']]['receita'].sum()
                organic_value = base_p[base_p['is_organic']]['receita'].sum()
                
                ads_rows.append({
                    'periodo': p,
                    'ads_pct': ads_qty / total,
                    'organic_pct': organic_qty / total,
                    'ads_qty': int(ads_qty),
                    'organic_qty': int(organic_qty),
                    'ads_value': float(ads_value),
                    'organic_value': float(organic_value)
                })
            else:
                ads_rows.append({
                    'periodo': p,
                    'ads_pct': 0,
                    'organic_pct': 0,
                    'ads_qty': 0,
                    'organic_qty': 0,
                    'ads_value': 0.0,
                    'organic_value': 0.0
                })
        
        df_ads = pd.DataFrame(ads_rows)
        
        return export, df_logistics, df_ads
