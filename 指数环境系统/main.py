from market_environment_system import MarketEnvironmentSystem


def main():
    """主程序入口"""
    # 创建系统实例
    # system = MarketEnvironmentSystem(index_symbol="sh000300", days=60)
    system = MarketEnvironmentSystem(
    index_symbol="sh000300", 
    days=60, 
    csv_path="./beixiangzijin.csv"
)
    # 运行分析
    system.run()
    
    # 打印结果
    system.print_results()
    
    # 保存结果
    system.save_results()
    
    return system


if __name__ == "__main__":
    main()
