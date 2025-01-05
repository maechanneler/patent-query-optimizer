from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from simplified_patent_search import SimplifiedPatentSearch
import argparse
import json
import logging
import pandas as pd
import time

def parse_args():
    parser = argparse.ArgumentParser(description="Patent Search Tool")
    parser.add_argument("--query", required=True, help="Search query for patents")
    parser.add_argument("--optimize", action="store_true", help="Optimize the search query")
    parser.add_argument("--results", type=int, default=100, help="Number of results to retrieve")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--iterations", type=int, default=3, help="Number of optimization iterations")
    parser.add_argument("--show-cache", action="store_true", help="Show cached patents after execution")
    return parser.parse_args()

def display_cached_patents():
    """キャッシュされている特許情報を表示"""
    cache_file = Path("patent_cache.json")
    if not cache_file.exists():
        print("\nキャッシュファイルが存在しません。")
        return

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)

        if not cache:
            print("\nキャッシュに特許情報が保存されていません。")
            return

        print("\n=== キャッシュされている特許情報 ===")
        for query, data in cache.items():
            print(f"\n検索クエリ: {query}")
            print(f"最終更新: {data['last_updated']}")
            patent = data['patent_data']
            print(f"特許番号: {patent.get('patent_number', 'N/A')}")
            print(f"タイトル: {patent.get('title', 'N/A')}")
            print(f"出願日: {patent.get('filing_date', 'N/A')}")
            print(f"発明者: {patent.get('inventors', 'N/A')}")
            print(f"出願人: {patent.get('assignee', 'N/A')}")
            print("-" * 50)

    except Exception as e:
        print(f"\nキャッシュファイルの読み込み中にエラーが発生しました: {str(e)}")

def save_query_history(query_history: pd.DataFrame, query: str) -> None:
    """検索履歴をCSVファイルとして保存"""
    try:
        # 検索履歴用のディレクトリを作成
        history_dir = Path("search_history")
        history_dir.mkdir(exist_ok=True)
        
        # ファイル名に日時とクエリの一部を含める
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # クエリから有効なファイル名を作成（特殊文字を除去）
        safe_query = "".join(c for c in query[:30] if c.isalnum() or c in (' ', '_')).strip()
        safe_query = safe_query.replace(' ', '_')
        
        filename = f"query_history_{timestamp}_{safe_query}.csv"
        filepath = history_dir / filename
        
        # CSVとして保存
        query_history.to_csv(filepath, index=False, encoding='utf-8')
        logging.info(f"検索履歴を保存しました: {filepath}")
        
    except Exception as e:
        logging.error(f"検索履歴の保存中にエラーが発生しました: {str(e)}")

def main():
    args = parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    load_dotenv()
    
    try:
        searcher = SimplifiedPatentSearch()
        current_query = args.query
        
        # 検索履歴を保存するDataFrame
        query_history = pd.DataFrame(columns=[
            'iteration',
            'query',
            'num_results',
            'evaluation',
            'timestamp'
        ])
        
        for iteration in range(args.iterations):
            logging.info(f"\nIteration {iteration + 1}/{args.iterations}")
            logging.info(f"Current query: {current_query}")
            
            # 検索実行
            results = searcher.search_patents(current_query, args.results)
            
            if results.empty:
                logging.warning("No results found")
                break
                
            logging.info(f"\nFound {len(results)} results")
            print("\nTop 10 results:")
            print(results[['title', 'abstract']].head(10))
            
            # 検索結果の評価
            evaluation = searcher.evaluate_search_results(current_query, results)
            print("\nEvaluation:")
            print(evaluation)
            
            # 検索履歴にデータを追加
            query_history = pd.concat([
                query_history,
                pd.DataFrame([{
                    'iteration': iteration + 1,
                    'query': current_query,
                    'num_results': len(results),
                    'evaluation': evaluation,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
            ], ignore_index=True)
            
            # クエリの最適化と次のイテレーション
            if args.optimize and iteration < args.iterations - 1:
                logging.info("\nOptimizing query for next iteration...")
                print("\nPrevious queries and their evaluations:")
                print(query_history[['query', 'evaluation']].to_string())
                
                # 既存の評価結果を含めてクエリを最適化
                current_query, _ = searcher.optimize_query(
                    current_query,
                    previous_queries=query_history['query'].tolist(),
                    previous_evaluations=query_history['evaluation'].tolist()
                )
                print(f"\nNext iteration will use query: {current_query}")
                time.sleep(1)  # API制限を考慮した待機
        
        # 検索履歴をファイルに保存
        save_query_history(query_history, args.query)
        
        # キャッシュされた特許情報の表示
        if args.show_cache:
            display_cached_patents()
            
    except Exception as e:
        logging.error(f"Error during execution: {str(e)}", exc_info=args.debug)

if __name__ == "__main__":
    main()
