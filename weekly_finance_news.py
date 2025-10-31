import requests
import datetime as dt

# === 配置区 ===
NEWS_API_KEY = "替换成你的NewsAPI_KEY"
KEYWORDS = "finance OR stocks OR economy OR market"
ARTICLES_LIMIT = 8  # 每周取多少条新闻

# === 日期范围（过去7天） ===
END_DATE = dt.date.today()
START_DATE = END_DATE - dt.timedelta(days=7)

# === 1. 获取新闻函数 ===
def fetch_weekly_finance_news():
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={KEYWORDS}&"
        f"from={START_DATE}&"
        f"to={END_DATE}&"
        f"language=en&"
        f"sortBy=popularity&"
        f"apiKey={NEWS_API_KEY}"
    )
    resp = requests.get(url)
    data = resp.json()

    if data.get("status") != "ok":
        raise ValueError(f"获取新闻失败：{data}")

    articles = data.get("articles", [])[:ARTICLES_LIMIT]
    news_list = []
    for art in articles:
        title = art.get("title", "").strip()
        source = art.get("source", {}).get("name", "N/A")
        published = art.get("publishedAt", "")[:10]
        url_link = art.get("url", "")
        news_list.append({
            "title": title,
            "source": source,
            "date": published,
            "url": url_link
        })
    return news_list

# === 2. 生成周报内容 ===
def generate_weekly_report(news_list):
    report = []
    report.append(f"# 📰 每周金融新闻总结\n")
    report.append(f"📅 周期：{START_DATE} - {END_DATE}\n")
    report.append("## 1. 本周重要新闻")

    for idx, n in enumerate(news_list, 1):
        report.append(f"{idx}. {n['title']}  \n来源: {n['source']} | 日期: {n['date']}  \n链接: {n['url']}")

    report.append("\n## 2. AI 自动投资观察（示例）")
    # 简易逻辑，这里你可以换成 ChatGPT API 调用
    if any("rate" in n['title'].lower() or "inflation" in n['title'].lower() for n in news_list):
        report.append("- 本周央行及通胀相关新闻较多，市场对利率预期敏感度较高。建议关注美债收益率和美元走势。")
    if any("stock" in n['title'].lower() or "earnings" in n['title'].lower() for n in news_list):
        report.append("- 美股及财报相关信息活跃，科技板块波动可能加大。")
    if any("oil" in n['title'].lower() or "gold" in n['title'].lower() for n in news_list):
        report.append("- 大宗商品价格变动显著，适合保持部分避险资产配置。")

    report.append("\n## 3. 下周关注重点")
    report.append("- 美国CPI/就业数据")
    report.append("- 中国PMI公布")
    report.append("- OPEC会议能源策略")

    return "\n".join(report)

# === 3. 主程序调用 ===
if __name__ == "__main__":
    try:
        news = fetch_weekly_finance_news()
        weekly_report = generate_weekly_report(news)
        filename = f"finance_weekly_{END_DATE}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(weekly_report)
        print(f"✅ 周报已生成：{filename}")
        print(weekly_report)  # 控制台输出

    except Exception as e:
        print(f"❌ 运行出错：{e}")