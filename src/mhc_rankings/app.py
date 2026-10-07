import argparse
import sys
from pathlib import Path

from .io import (
    get_latest_game_date,
    load_games_data,
    save_colley_matrix_tsv,
    save_rankings_tsv,
    save_weekly_ratings_tsv,
)
from .console import print_rankings_table
from .plotting import save_matplotlib_plot
from .rankings_math import compute_weekly_ratings, compute_final_rankings, compute_team_game_logs
from .reporting import generate_html_report, generate_team_reports


def main() -> None:
    parser = argparse.ArgumentParser(description="MHC Hockey Colley Matrix Rankings Generator")
    parser.add_argument(
        "--input", 
        type=str, 
        required=True, 
        help="Path to the input TSV file containing game results."
    )
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default=".", 
        help="Directory to save the generated report and data files."
    )
    parser.add_argument(
        "--plot-engine", 
        type=str, 
        choices=["matplotlib", "plotly"], 
        default="plotly",
        help="The plotting engine to use in the HTML report."
    )
    parser.add_argument(
        "--skip-raw", 
        action="store_true", 
        help="Skip saving the raw TSV and PNG files."
    )
    # parser.add_argument(
    #     "--include-sos-plot", 
    #     action="store_true", 
    #     help="Include a progress plot of the Strength of Schedule in the HTML report."
    # )
    
    parser.add_argument(
        "--method",
        type=str,
        choices=["colley", "bt-elo"],
        default="colley",
        help="The ranking methodology to use (Colley Matrix or Bradley-Terry/Elo hybrid)."
    )
    parser.add_argument(
        "--use-movm",
        action="store_true",
        help="Use Margin of Victory Multiplier for BT-Elo."
    )
    parser.add_argument(
        "--max-gd",
        type=int,
        default=4,
        help="Maximum goal differential used in MoVM calculation (BT-Elo only)."
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading data from {input_path}...")
    df = load_games_data(input_path)
    
    if df.empty:
        print("Error: No data found in the input file.", file=sys.stderr)
        sys.exit(1)
        
    engine_kwargs = {}
    if args.method == "bt-elo":
        engine_kwargs["use_movm"] = args.use_movm
        engine_kwargs["max_gd"] = args.max_gd
        
    latest_date = get_latest_game_date(df)
    print(f"Latest game date identified as: {latest_date}")
    
    print(f"Computing {args.method} matrix/ratings and rankings...")
    rankings, details, teams = compute_final_rankings(df, method=args.method, **engine_kwargs)
    
    print("Computing weekly ratings progress...")
    weekly_records, _ = compute_weekly_ratings(df, method=args.method, **engine_kwargs)
    
    # Calculate rank_change for final rankings
    if weekly_records:
        sorted_weeks = sorted(weekly_records.keys())
        if len(sorted_weeks) >= 2:
            prev_week = sorted_weeks[-2]
            prev_records = weekly_records[prev_week]
            prev_ranks = {rec.team: idx + 1 for idx, rec in enumerate(prev_records)}
        else:
            prev_ranks = {rec.team: idx + 1 for idx, rec in enumerate(weekly_records[sorted_weeks[0]])}
            
        for idx, rec in enumerate(rankings):
            current_rank = idx + 1
            rec.rank_change = prev_ranks.get(rec.team, current_rank) - current_rank
    
    if not args.skip_raw:
        rankings_file = output_dir / "rankings_output.tsv"
        weekly_file = output_dir / "weekly_ratings_output.tsv"
        plot_file = output_dir / "weekly_ratings_plot.png"
        rank_plot_file = output_dir / "weekly_rankings_plot.png"
        
        print("Saving raw data files...")
        save_rankings_tsv(rankings, rankings_file)
        save_weekly_ratings_tsv(weekly_records, teams, weekly_file)
        
        title_method = "Colley" if args.method == "colley" else "Bradley-Terry Elo"
        save_matplotlib_plot(weekly_records, teams, plot_file, f"MHC {title_method} Ratings Plot", f"{title_method} Rating", metric="rating")
        save_matplotlib_plot(weekly_records, teams, rank_plot_file, "Rankings Progress", "Rank", metric="rank")
        
        # if args.include_sos_plot:
        sos_plot_file = output_dir / "weekly_sos_plot.png"
        save_matplotlib_plot(weekly_records, teams, sos_plot_file, "Strength of Schedule Progress", "SOS", metric="sos")
            
        if args.method == "colley":
            matrix_file = output_dir / "colley_matrix_output.tsv"
            save_colley_matrix_tsv(details, teams, matrix_file)
        
    report_file = output_dir / "mhc_rankings_report.html"
    print(f"Generating HTML report ({args.plot_engine})...")
    generate_html_report(
        date_str=latest_date,
        rankings=rankings,
        details=details,
        teams=teams,
        weekly_records=weekly_records,
        plot_engine=args.plot_engine,
        output_path=report_file,
        df=df,
        include_sos_plot=True,
        method=args.method,
        use_movm=args.use_movm
    )
    
    print(f"Done! Report saved to {report_file}")
    
    print("Computing team game logs...")
    team_logs = compute_team_game_logs(df, method=args.method, **engine_kwargs)
    team_report_file = output_dir / "mhc_team_reports.html"
    print(f"Generating Team Reports ({args.plot_engine})...")
    generate_team_reports(
        date_str=latest_date,
        rankings=rankings,
        team_logs=team_logs,
        plot_engine=args.plot_engine,
        output_path=str(team_report_file),
        method=args.method,
        use_movm=args.use_movm
    )
    print(f"Team Reports saved to {team_report_file}")
    
    print_rankings_table(rankings, method=args.method)


if __name__ == "__main__":
    main()
