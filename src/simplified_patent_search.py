from datetime import datetime
from openai import OpenAI
from pathlib import Path
from serpapi import GoogleSearch
from typing import Dict, Optional
import json
import logging
import os
import pandas as pd
import time

logger = logging.getLogger(__name__)

class PatentCache:
    def __init__(self, cache_file: str = "patent_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """キャッシュファイルを読み込む"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_cache(self) -> None:
        """キャッシュをファイルに保存する"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def update_cache(self, query: str, patent_data: dict) -> None:
        """クエリに対する最適な特許情報をキャッシュに保存"""
        self.cache[query] = {
            "patent_data": patent_data,
            "last_updated": datetime.now().isoformat()
        }
        self._save_cache()

    def get_cached_patent(self, query: str) -> dict:
        """クエリに対するキャッシュされた特許情報を取得"""
        return self.cache.get(query, {}).get("patent_data", {})

    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        self.cache = {}
        self._save_cache()

class SimplifiedPatentSearch:
    def __init__(self, api_key: Optional[str] = None, openai_api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('SERPAPI_KEY')
        if not self.api_key:
            raise ValueError("SERPAPI API key must be provided")
        
        self.openai_api_key = openai_api_key or os.environ.get('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API key must be provided")
        
        self.client = OpenAI(api_key=self.openai_api_key)
        self.model = "gpt-4o-mini"
        # キャッシュインスタンスを初期化
        self.cache = PatentCache()

    def _normalize_patent_number(self, patent_number: str) -> str:
        """特許番号を正規化する"""
        # 空白、ハイフン、その他の区切り文字を削除
        normalized = ''.join(filter(str.isalnum, patent_number))
        return normalized.upper()

    def _get_most_relevant_patent(self, query: str, patents_df: pd.DataFrame) -> dict:
        """検索結果から最も関連性の高い特許を特定"""
        if patents_df.empty:
            logger.warning("Empty patents DataFrame provided")
            return {}

        try:
            # 結果を制限して処理
            sample_patents = patents_df.head(10)  # 最初の10件のみを使用
            
            # 特許番号を正規化してDataFrameに追加
            sample_patents['normalized_patent_number'] = sample_patents['patent_number'].apply(self._normalize_patent_number)
            
            system_prompt = """あなたは特許検索の専門家です。
与えられた検索クエリに対して、検索結果の中から最も関連性の高い特許を1つ選んでください。
特許番号は完全な形式で返してください（例: JP2020123456A）。"""

            user_message = f"""検索クエリ: {query}

検索結果（上位10件）:
{sample_patents[['title', 'abstract', 'patent_number']].to_string()}

最も関連性の高い特許の番号を返してください。特許番号だけを返し、説明は不要です。"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            most_relevant_patent_number = response.choices[0].message.content.strip()
            normalized_response = self._normalize_patent_number(most_relevant_patent_number)
            
            # 正規化された特許番号で検索
            most_relevant_patent = sample_patents[
                sample_patents['normalized_patent_number'] == normalized_response
            ].to_dict('records')
            
            if not most_relevant_patent:
                logger.warning(f"No matching patent found for number: {most_relevant_patent_number}")
                # 最初の特許を返すフォールバック
                return sample_patents.iloc[0].to_dict()
            
            return most_relevant_patent[0]

        except Exception as e:
            logger.error(f"Error finding most relevant patent: {str(e)}")
            if not patents_df.empty:
                # エラー時は最初の特許を返す
                return patents_df.iloc[0].to_dict()
            return {}

    def search_patents(self, query: str, num_results: int = 100) -> pd.DataFrame:
        """特許検索を実行する"""
        params = {
            "engine": "google_patents",
            "q": query,
            "api_key": self.api_key,
            "num": num_results,
            "hl": "ja",
            "patent": "JP",
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "organic_results" not in results:
                logger.error("No results found")
                return pd.DataFrame()

            patents = []
            for patent in results["organic_results"]:
                patent_data = {
                    "title": patent.get("title", ""),
                    "patent_number": patent.get("patent_number", ""),
                    "filing_date": patent.get("filing_date", ""),
                    "publication_date": patent.get("publication_date", ""),
                    "inventors": ", ".join(patent.get("inventors", [])),
                    "assignee": patent.get("assignee", ""),
                    "abstract": patent.get("snippet", ""),
                    "link": patent.get("link", "")
                }
                patents.append(patent_data)

            df = pd.DataFrame(patents)
            
            # 最も関連性の高い特許を特定してキャッシュに保存
            if not df.empty:
                most_relevant_patent = self._get_most_relevant_patent(query, df)
                if most_relevant_patent:
                    self.cache.update_cache(query, most_relevant_patent)
                    logger.info(f"Updated cache for query: {query}")
                    logger.info(f"Most relevant patent: {most_relevant_patent.get('patent_number', 'Unknown')}")
            
            return df

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return pd.DataFrame()

    def evaluate_search_results(self, query: str, df: pd.DataFrame) -> str:
        """検索結果を評価する"""
        if df.empty:
            return "検索結果が得られませんでした。"
            
        try:
            # 結果を制限して処理
            sample_results = df.head(5)  # 最初の5件のみを使用
            
            system_prompt = """あなたは特許検索結果を評価する専門家です。
検索クエリと結果を分析し、結果の質について1段落で簡潔に評価してください。"""
            
            user_message = f"""検索クエリ: {query}

検索結果（最初の5件）:
{sample_results[['title', 'abstract']].to_string()}"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as err:
            logger.error(f"Evaluation error: {str(err)}")
            return f"評価中にエラーが発生しました: {str(err)}"

    def optimize_query(self, query: str,
                      previous_queries: list = None,
                      previous_evaluations: list = None) -> tuple[str, str]:
        """検索式を最適化する"""
        try:
            # 現在のクエリで検索を実行
            results = self.search_patents(query)
            evaluation = self.evaluate_search_results(query, results)
            
            # 結果件数を取得
            result_count = len(results)
            
            system_prompt = """あなたは特許検索クエリを最適化する専門家です。
過去の検索履歴と評価結果を参考に、より良い検索結果が得られるようクエリを1つ提案してください。

重要な指示:
1. 検索結果が0件の場合:
   - まず、より上位の概念を使用してクエリを作成してください
   - 例: 「空飛ぶ自動車の折りたたみ式翼」→「自動車用の可変構造翼」
   
2. 検索結果が多すぎる場合（1000件以上）:
   - より具体的な下位概念を使用してクエリを作成してください
   - 例: 「自動運転」→「市街地での自動運転制御方法」

3. 適度な結果件数（1-1000件）の場合:
   - 現在の抽象度を維持しながら、関連性の高い結果が得られるようクエリを最適化してください

クエリだけを返してください。余分な説明や「提案クエリ：」などのプレフィックスは不要です。"""

            # 検索履歴と評価の文字列を制限
            def truncate_text(text: str, max_length: int = 200) -> str:
                return text[:max_length] + "..." if len(text) > max_length else text

            user_message = f"""
基本クエリ: {query}
現在の検索結果件数: {result_count}
現在の評価結果: {truncate_text(evaluation)}

"""
            # 過去の検索履歴がある場合は追加（制限付き）
            if previous_queries and previous_evaluations:
                user_message += "過去の検索履歴（要約）:\n"
                for prev_query, prev_eval in zip(previous_queries[-3:], previous_evaluations[-3:]):  # 最新の3件のみ
                    user_message += f"クエリ: {prev_query}\n評価: {truncate_text(prev_eval)}\n\n"

            user_message += """上記の情報を基に、より良い検索クエリを1つ提案してください。
特に、検索結果件数に基づいて適切な抽象度のクエリを提案してください。"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )

            improved_query = response.choices[0].message.content.strip()
            # "提案クエリ: "などのプレフィックスを削除
            for prefix in ["提案クエリ: ", "改善クエリ: ", "最適化クエリ: "]:
                if improved_query.startswith(prefix):
                    improved_query = improved_query[len(prefix):]
            improved_query = improved_query.strip()
            
            # 最適化の経過を記録
            if result_count == 0:
                logger.info(f"検索結果が0件のため、より上位の概念でクエリを最適化: {improved_query}")
            elif result_count > 1000:
                logger.info(f"検索結果が多すぎるため、より具体的な概念でクエリを最適化: {improved_query}")
            else:
                logger.info(f"適度な結果件数のため、関連性を重視してクエリを最適化: {improved_query}")
            
            return improved_query, evaluation

        except Exception as e:
            logger.error(f"Query optimization error: {str(e)}")
            return query, f"最適化中にエラーが発生しました: {str(e)}"

    def get_cached_patent(self, query: str) -> dict:
        """クエリに対するキャッシュされた特許情報を取得"""
        return self.cache.get_cached_patent(query)

    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        self.cache.clear_cache()
