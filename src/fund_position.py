class FundPosition:
    """Track position cost, share count, and cash movements for a single fund."""

    def __init__(self):
        self.total_cost = 0.0   # Total cost (cash invested)
        self.total_shares = 0.0 # Current share balance

        self.total_cash_dividends = 0.0     # All dividends received
        self.holding_cash_dividends = 0.0   # Dividends tied to the remaining position

        self.net_trade_cash = 0.0

    def buy(self, cash, shares):
        self.total_cost += cash
        self.total_shares += shares
        self.net_trade_cash -= cash
        
    def sell(self, cash, shares):
        shares_to_sell = shares
        if shares_to_sell > self.total_shares:
            raise ValueError("Sell quantity exceeds current share balance")
        
        sell_ratio = shares_to_sell / self.total_shares
        cost_to_deduct = sell_ratio * self.total_cost
        self.total_cost -= cost_to_deduct
        self.total_shares -= shares_to_sell

        # Reduce dividends associated with the sold proportion
        self.holding_cash_dividends -= sell_ratio * self.holding_cash_dividends

        self.net_trade_cash += cash

        if self.total_shares == 0:
            self.holding_cash_dividends = 0

    def income(self, cash=0, shares=0):
        if cash and cash > 0:
            self.total_cash_dividends += cash
            self.holding_cash_dividends += cash
        if shares and shares > 0:
            self.total_shares += shares    

    def average_cost_per_unit(self):
        if self.total_shares == 0:
            return 0.0
        return self.total_cost / self.total_shares
    
    def status(self):
        print(f"Total cost: {self.total_cost: .2f}, total shares: {self.total_shares: .2f}")
        print(f"Average cost per unit: {self.average_cost_per_unit(): .4f}")
