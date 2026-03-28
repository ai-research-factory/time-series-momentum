# Time Series Momentum

## Project ID
proj_373a65da

## Taxonomy
StatArb

## Current Cycle
3

## Objective
Implement, validate, and iteratively improve the paper's approach with production-quality standards.


## Design Brief
### Problem
The paper investigates the existence and profitability of a 'time series momentum' effect, which is distinct from the well-known cross-sectional momentum. The core problem is to determine if a simple trend-following strategy, applied individually across a diverse set of liquid futures contracts, can generate significant risk-adjusted returns. The paper posits that such a strategy is not only profitable but also exhibits desirable properties, such as performing particularly well during market crises and being robust to transaction costs, making it a valuable addition to a traditional investment portfolio.

### Datasets
{"name":"Proxy Universe via yfinance","source":"yfinance API","details":"A curated list of ~20-30 tickers representing the four asset classes. Equities: SPY, QQQ, EWJ, EEM. Bonds: TLT, IEF, BND. Commodities: GLD, USO, DBC. Currencies: EURUSD=X, JPY=X, GBPUSD=X, AUDUSD=X. Daily OHLCV data will be downloaded."}

### Targets
The primary target is to generate a portfolio with a high, statistically significant Sharpe ratio. Secondary targets include achieving positive returns during market crises and demonstrating profitability after realistic transaction costs.

### Model
The model is a simple trend-following rule applied to individual time series. The trading signal for each asset is the sign of its excess return over a lookback period 'k' (e.g., 12 months). To manage risk, each position is scaled by the inverse of its recent historical volatility (e.g., 60-day standard deviation) to target a constant ex-ante volatility. The final portfolio is an equally weighted combination of these individual, volatility-scaled strategies.

### Training
This is a backtesting-based study, not a traditional machine learning model with a training phase. The 'parameters' of the model, such as the lookback period 'k', are pre-defined based on the paper's analysis (k=12 months is the primary setting). The evaluation is performed over the entire available history using a rolling-window approach where signals are calculated based on past data only.

### Evaluation
The primary evaluation metric is the annualized Sharpe ratio of the net-of-costs portfolio returns. Other key metrics include mean annualized return, standard deviation, skewness, and maximum drawdown. Performance will be evaluated for the diversified portfolio as a whole, as well as for sub-portfolios of each asset class. A crucial part of the evaluation is analyzing performance during specific market crisis periods (e.g., 2008 GFC, 2020 COVID-19 crash).


## データ取得方法（共通データ基盤）

**合成データの自作は禁止。以下のARF Data APIからデータを取得すること。**

### ARF Data API
```bash
# OHLCV取得 (CSV形式)
curl -o data/aapl_1d.csv "https://ai.1s.xyz/api/data/ohlcv?ticker=AAPL&interval=1d&period=5y"
curl -o data/btc_1h.csv "https://ai.1s.xyz/api/data/ohlcv?ticker=BTC/USDT&interval=1h&period=1y"
curl -o data/nikkei_1d.csv "https://ai.1s.xyz/api/data/ohlcv?ticker=^N225&interval=1d&period=10y"

# JSON形式
curl "https://ai.1s.xyz/api/data/ohlcv?ticker=AAPL&interval=1d&period=5y&format=json"

# 利用可能なティッカー一覧
curl "https://ai.1s.xyz/api/data/tickers"
```

### Pythonからの利用
```python
import pandas as pd
API = "https://ai.1s.xyz/api/data/ohlcv"
df = pd.read_csv(f"{API}?ticker=AAPL&interval=1d&period=5y")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.set_index("timestamp")
```

### ルール
- **リポジトリにデータファイルをcommitしない** (.gitignoreに追加)
- 初回取得はAPI経由、以後はローカルキャッシュを使う
- data/ディレクトリは.gitignoreに含めること



## ★ 今回のタスク (Cycle 2)


### Phase 2: データパイプライン構築 [Track ]

**Track**:  (A=論文再現 / B=近傍改善 / C=独自探索)
**ゴール**: 複数資産の価格データをyfinanceから取得し、前処理して保存する。

**具体的な作業指示**:
src/data_loader.py に `DataLoader` クラスを作成する。コンフィグファイル（`config/assets.yaml`）で定義されたティッカーリスト（SPY, GLD, TLT, EURUSD=Xなど約20銘柄）を読み込み、`yfinance.download` を使用して日次価格データを取得する（`period='max'`, `interval='1d'`）。取得したデータは、'Adj Close'のみを抽出し、一つのDataFrameに結合する。日付でアライメントし、NaN値を前方フィルで埋める。最終的なDataFrameを `data/processed/prices.parquet` として保存する。`scripts/download_data.py` を作成し、このクラスを呼び出して実行できるようにする。

**期待される出力ファイル**:
- src/data_loader.py
- scripts/download_data.py
- config/assets.yaml
- data/processed/prices.parquet

**受入基準 (これを全て満たすまで完了としない)**:
- `scripts/download_data.py` を実行すると `data/processed/prices.parquet` が生成されること。
- Parquetファイルには`config/assets.yaml`で定義した全資産の日次価格データが含まれていること。










## 全体Phase計画 (参考)

✓ Phase 1: コアシグナル実装 — 単一資産の時系列モメンタムシグナルを計算する関数を実装する。
✓ Phase 2: データパイプライン構築 — 複数資産の価格データをyfinanceから取得し、前処理して保存する。
→ Phase 3: 基本バックテストとボラティリティスケーリング — ボラティリティスケーリングを含むベクトル化バックテスターを実装し、ポートフォリオのグロスリターンを計算する。
  Phase 4: 取引コストモデルの実装 — 取引コストを考慮したネットリターンを計算し、グロスリターンと比較する。
  Phase 5: ルックバック期間の最適化 — 複数のルックバック期間で戦略を評価し、パフォーマンスを比較する。
  Phase 6: ロバスト性検証：資産クラス別分析 — 戦略パフォーマンスを資産クラス（株式、債券、通貨、コモディティ）ごとに分解して分析する。
  Phase 7: ボラティリティ目標値の感度分析 — ターゲットボラティリティの値を変更し、戦略パフォーマンスへの影響を分析する。
  Phase 8: 代替シグナル定義の比較 — 移動平均クロスオーバーを代替シグナルとして実装し、論文手法と比較する。
  Phase 9: 市場危機時のパフォーマンス分析 — 主要な市場危機（2008年金融危機、2020年コロナショック）における戦略のパフォーマンスを定量化する。
  Phase 10: レポートと可視化 — 論文の図表を模倣した包括的な結果レポートと可視化を生成する。
  Phase 11: コード品質向上と最終化 — コードベース全体の品質を向上させ、ドキュメントを整備する。
  Phase 12: エグゼクティブサマリー作成 — 非技術者向けに、プロジェクトの発見事項をまとめた日本語のエグゼクティブサマリーを作成する。


## 評価原則
- **主指標**: Sharpe ratio (net of costs) on out-of-sample data
- **Walk-forward必須**: 単一のtrain/test splitでの最終評価は不可
- **コスト必須**: 全メトリクスは取引コスト込みであること
- **安定性**: Walk-forward窓の正の割合を報告
- **ベースライン必須**: 必ずナイーブ戦略と比較

## 再現モードのルール（論文忠実度の維持）

このプロジェクトは**論文再現**が目的。パフォーマンス改善より論文忠実度を優先すること。

### パラメータ探索の制約
- **論文で既定されたパラメータをまず実装し、そのまま評価すること**
- パラメータ最適化を行う場合、**論文既定パラメータの近傍のみ**を探索（例: 論文が12ヶ月なら [6, 9, 12, 15, 18] ヶ月）
- 論文と大きく異なるパラメータ（例: 月次論文に対して日次10営業日）で良い結果が出ても、それは「論文再現」ではなく「独自探索」
- 独自探索で得た結果は `customMetrics` に `label: "implementation-improvement"` として記録し、論文再現結果と明確に分離

### データ条件の忠実度
- 論文のデータ頻度（日次/月次/tick）にできるだけ合わせる
- ユニバース規模が論文より大幅に小さい場合、その制約を `docs/open_questions.md` に明記
- リバランス頻度・加重方法も論文に合わせる



## 禁止事項
- 未来情報を特徴量やシグナルに使わない
- 全サンプル統計でスケーリングしない (train-onlyで)
- テストセットでハイパーパラメータを調整しない
- コストなしのgross PnLだけで判断しない
- 時系列データにランダムなtrain/test splitを使わない
- APIキーやクレデンシャルをコミットしない
- **新しい `scripts/run_cycle_N.py` や `scripts/experiment_cycleN.py` を作成しない。既存の `src/` 内ファイルを修正・拡張すること**
- **合成データを自作しない。必ずARF Data APIからデータを取得すること**
- **「★ 今回のタスク」以外のPhaseの作業をしない。1サイクル=1Phase**
- **論文が既定するパラメータから大幅に逸脱した探索を「再現」として報告しない**

## Git / ファイル管理ルール
- **データファイル(.csv, .parquet, .h5, .pkl, .npy)は絶対にgit addしない**
- `__pycache__/`, `.pytest_cache/`, `*.pyc` がリポジトリに入っていたら `git rm --cached` で削除
- `git add -A` や `git add .` は使わない。追加するファイルを明示的に指定する
- `.gitignore` を変更しない（スキャフォールドで設定済み）
- データは `data/` ディレクトリに置く（.gitignore済み）
- 学習済みモデルは `models/` ディレクトリに置く（.gitignore済み）

## 出力ファイル
以下のファイルを保存してから完了すること:
- `reports/cycle_3/metrics.json` — 下記スキーマに従う（必須）
- `reports/cycle_3/technical_findings.md` — 実装内容、結果、観察事項

### metrics.json 必須スキーマ
```json
{
  "sharpeRatio": 0.0,
  "annualReturn": 0.0,
  "maxDrawdown": 0.0,
  "hitRate": 0.0,
  "totalTrades": 0,
  "transactionCosts": { "feeBps": 10, "slippageBps": 5, "netSharpe": 0.0 },
  "walkForward": { "windows": 0, "positiveWindows": 0, "avgOosSharpe": 0.0 },
  "customMetrics": {}
}
```
- 全フィールドを埋めること。Phase 1-2で未実装のメトリクスは0.0/0で可。
- `customMetrics`に論文固有の追加メトリクスを自由に追加してよい。
- `docs/open_questions.md` — 未解決の疑問と仮定
- `README.md` — 今回のサイクルで変わった内容を反映して更新（セットアップ手順、主要な結果、使い方など）
- `docs/open_questions.md` に以下も記録:
  - ARF Data APIで問題が発生した場合（エラー、データ不足、期間の短さ等）
  - CLAUDE.mdの指示で不明確な点や矛盾がある場合
  - 環境やツールの制約で作業が完了できなかった場合

## 標準バックテストフレームワーク

`src/backtest.py` に以下が提供済み。ゼロから書かず、これを活用すること:
- `WalkForwardValidator` — Walk-forward OOS検証のtrain/test split生成
- `calculate_costs()` — ポジション変更に基づく取引コスト計算
- `compute_metrics()` — Sharpe, 年率リターン, MaxDD, Hit rate算出
- `generate_metrics_json()` — ARF標準のmetrics.json生成

```python
from src.backtest import WalkForwardValidator, BacktestConfig, calculate_costs, compute_metrics, generate_metrics_json
```

## Key Commands
```bash
pip install -e ".[dev]"
pytest tests/
python -m src.cli run-experiment --config configs/default.yaml
```

Commit all changes with descriptive messages.
