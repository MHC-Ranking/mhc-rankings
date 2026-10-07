import pandas as pd
from jinja2 import Environment, FileSystemLoader
import os

from mhc_rankings.teams import team_to_abbrev

def load_data():
    # Load committee rankings
    mhc_df = pd.read_csv('data/mhc-hockey/mhc-committe-rankings.tsv', sep='\t')
    mhc_df.rename(columns={'MHC Ranking': 'mhc_rank'}, inplace=True)
    mhc_df['mhc_rank'] = pd.to_numeric(mhc_df['mhc_rank'], errors='coerce')
    
    # Load Colley rankings
    colley_df = pd.read_csv('data/mhc-hockey/colley/rankings_output.tsv', sep='\t')
    # Load BT-Elo rankings
    bt_df = pd.read_csv('data/mhc-hockey/bt-elo/rankings_output.tsv', sep='\t')
    # Load BT-Elo-MoVM rankings
    bt_movm_df = pd.read_csv('data/mhc-hockey/bt-elo-movm/rankings_output.tsv', sep='\t')
    # Load BT-Elo-MoVM-Rev rankings
    bt_movm_rev_df = pd.read_csv('data/mhc-hockey/bt-elo-movm-rev/rankings_output.tsv', sep='\t')

    # Merge dataframes
    merged_df = mhc_df.copy()

    # Get win % from one of the output files
    win_pct_df = colley_df[['Team', 'Raw Win%']].rename(columns={'Raw Win%': 'win_pct'})
    merged_df = pd.merge(merged_df, win_pct_df, on='Team', how='left')

    def add_method_cols(df_merged, df_method, prefix):
        df_sub = df_method[['Team', 'Rank', 'Rating', 'SOS']].copy()
        df_sub.rename(columns={
            'Rank': f'{prefix}_rank',
            'Rating': f'{prefix}_rating',
            'SOS': f'{prefix}_sos'
        }, inplace=True)
        return pd.merge(df_merged, df_sub, on='Team', how='left')

    merged_df = add_method_cols(merged_df, colley_df, 'colley')
    merged_df = add_method_cols(merged_df, bt_df, 'bt')
    merged_df = add_method_cols(merged_df, bt_movm_df, 'bt_movm')
    merged_df = add_method_cols(merged_df, bt_movm_rev_df, 'bt_movm_rev')

    # Calculate differences (MHC Rank - Method Rank)
    for prefix in ['colley', 'bt', 'bt_movm', 'bt_movm_rev']:
        merged_df[f'{prefix}_diff'] = merged_df['mhc_rank'] - merged_df[f'{prefix}_rank']

    # Sort by MHC Rank as the default
    merged_df.sort_values('mhc_rank', inplace=True)

    # Convert to list of dicts for Jinja
    teams_data = []
    for _, row in merged_df.iterrows():
        team_name = row['Team']
        team_dict = {
            'team': team_to_abbrev.get(team_name, team_name),
            'mhc_rank': int(row['mhc_rank']) if pd.notnull(row['mhc_rank']) else '-',
            'win_pct': row['win_pct'],
            
            'colley_rank': int(row['colley_rank']) if pd.notnull(row['colley_rank']) else '-',
            'colley_diff': int(row['colley_diff']) if pd.notnull(row['colley_diff']) else 0,
            'colley_rating': row['colley_rating'],
            'colley_sos': row['colley_sos'],

            'bt_rank': int(row['bt_rank']) if pd.notnull(row['bt_rank']) else '-',
            'bt_diff': int(row['bt_diff']) if pd.notnull(row['bt_diff']) else 0,
            'bt_rating': row['bt_rating'],
            'bt_sos': row['bt_sos'],

            'bt_movm_rank': int(row['bt_movm_rank']) if pd.notnull(row['bt_movm_rank']) else '-',
            'bt_movm_diff': int(row['bt_movm_diff']) if pd.notnull(row['bt_movm_diff']) else 0,
            'bt_movm_rating': row['bt_movm_rating'],
            'bt_movm_sos': row['bt_movm_sos'],

            'bt_movm_rev_rank': int(row['bt_movm_rev_rank']) if pd.notnull(row['bt_movm_rev_rank']) else '-',
            'bt_movm_rev_diff': int(row['bt_movm_rev_diff']) if pd.notnull(row['bt_movm_rev_diff']) else 0,
            'bt_movm_rev_rating': row['bt_movm_rev_rating'],
            'bt_movm_rev_sos': row['bt_movm_rev_sos'],
        }
        teams_data.append(team_dict)
    
    return teams_data

def generate_report():
    teams_data = load_data()
    
    env = FileSystemLoader('src/mhc_rankings/templates')
    template_env = Environment(loader=env)
    
    # Custom filter for abs function, since Jinja2 has `abs` built-in but just in case
    # we can use the default `abs` which is built-in standard filter `abs`.
    
    template = template_env.get_template('compare.html')
    
    html_out = template.render(teams=teams_data)
    
    os.makedirs('data/mhc-hockey', exist_ok=True)
    out_path = 'data/mhc-hockey/ranking_methods_comparison.html'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_out)
    
    print(f"Generated {out_path}")

if __name__ == '__main__':
    generate_report()
