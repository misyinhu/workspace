import yfinance as yf

d = yf.download("2513.HK", period="2y", progress=False)
print("OK:", len(d))
