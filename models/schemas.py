# Pydantic schemas matching frontend TypeScript types exactly
from pydantic import BaseModel
from typing import List, Optional, Literal


class AgentChip(BaseModel):
    icon: str
    label: str


class Signal(BaseModel):
    symbol: str
    name: str
    score: int
    type: Literal["BUY", "SELL", "HOLD"]
    potential: str
    agents: List[AgentChip]


class MarketData(BaseModel):
    name: str
    price: float
    change: float
    sparkline: List[float]


class ChartPoint(BaseModel):
    date: str
    price: float


class TechnicalAgent(BaseModel):
    rsi: float
    macd: str
    bollinger: str
    verdict: str


class FundamentalAgent(BaseModel):
    revenue: str
    profit: str
    highlight: str
    verdict: str


class InsiderAgent(BaseModel):
    recent: str
    holding: str
    pledge: str
    verdict: str


class SentimentAgent(BaseModel):
    articles: int
    score: float
    theme: str
    verdict: str


class FusionAgent(BaseModel):
    convergence: str
    backtest: str
    confidence: int
    verdict: str


class AgentsDetail(BaseModel):
    technical: TechnicalAgent
    fundamental: FundamentalAgent
    insider: InsiderAgent
    sentiment: SentimentAgent
    fusion: FusionAgent


class BacktestResult(BaseModel):
    days: int
    # Using alias since 'return' is reserved
    return_pct: float

    class Config:
        populate_by_name = True

    def model_dump(self, **kwargs):
        d = super().model_dump(**kwargs)
        d["return"] = d.pop("return_pct")
        return d


class StockAnalysis(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    score: int
    chartData: List[ChartPoint]
    agents: AgentsDetail
    backtest: List[BacktestResult]
    successRate: int


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    agents: Optional[List[str]] = None
    sources: Optional[List[str]] = None


class Holding(BaseModel):
    symbol: str
    qty: int
    buyPrice: float
    currentPrice: float


class PortfolioRequest(BaseModel):
    holdings: List[Holding]
