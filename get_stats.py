from core.trader import TradeStats


def main():
    trade_stats = TradeStats()
    trade_stats.send_stats_email()


if __name__ == "__main__":
    main()
