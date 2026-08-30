
from AlgorithmImports import *


class KRXEquity(PythonData):
    """한국 주식/ETF 커스텀 데이터"""

    def GetSource(self, config, date, isLive):
        symbol = config.Symbol.Value.lower()
        source = f"/Data/equity/krx/daily/{symbol}.csv"
        return SubscriptionDataSource(source, SubscriptionTransportMedium.LocalFile, FileFormat.Csv)

    def Reader(self, config, line, date, isLive):
        if not line.strip():
            return None

        data = KRXEquity()
        data.Symbol = config.Symbol
        try:
            cols = line.split(",")
            data.Time = datetime.strptime(cols[0], "%Y%m%d")
            data.Value = float(cols[4])
            data["Open"] = float(cols[1])
            data["High"] = float(cols[2])
            data["Low"] = float(cols[3])
            data["Close"] = float(cols[4])
            data["Volume"] = int(cols[5])
        except Exception:
            return None
        return data


class MonthlyFiveETFRebalance(QCAlgorithm):
    """매월 첫 데이터일에 5개 ETF를 18%씩 맞춘다."""

    def Initialize(self):
        self.SetStartDate(2021, 6, 27)
        self.SetEndDate(2026, 6, 27)
        self.SetCash(100000000)
        self.target_weight = 0.18
        self.last_rebalance_month = None
        self.symbols = []

        for ticker in ['069500', '133690', '114260', '153130', '132030']:
            symbol = self.AddData(KRXEquity, ticker, Resolution.Daily).Symbol
            self.symbols.append(symbol)

    def OnData(self, data):
        if any(not data.ContainsKey(symbol) for symbol in self.symbols):
            return

        month_key = self.Time.strftime("%Y-%m")
        if self.last_rebalance_month == month_key:
            return

        self.last_rebalance_month = month_key
        for symbol in self.symbols:
            self.SetHoldings(symbol, self.target_weight)
            self.Debug(f"rebalance {self.Time.date()} {symbol.Value} -> {self.target_weight:.2f}")
