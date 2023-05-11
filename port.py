import vectorbtpro as vbt

class Portfolio:
    
    def __init__(
        self,
        cash: float = 100.0,
    ) -> None:
        
        self.port = vbt.pf_enums.ExecState(
            cash=cash,
            position=0.0,
            debt=0.0,  
            locked_cash=0.0,  
            free_cash=cash,
            val_price=0.0,
            value=0.0
        )
    
    def get_position(self) -> float:
        return self.port.position

    def get_cash(self) -> float:
        return self.port.cash
    
    def create_order(
        self,
        size : float,
        price : float,
        direction : float
    ) -> vbt.portfolio.enums.Order:
        
        order = vbt.pf_nb.order_nb(
            size=size,
            price=price,
            direction=direction,
            size_granularity=1.0,
            log=True
        )
        return order
    
    def create_long_order(self, size: float, price: float,) -> vbt.portfolio.enums.Order:
        order = self.create_order(
            size=size,
            price=price,
            direction=0
        )
        return order

    def create_short_order(self, size: float, price: float,) -> vbt.portfolio.enums.Order:
        order = self.create_order(
            size=size,
            price=price,
            direction=1
        )
        return order