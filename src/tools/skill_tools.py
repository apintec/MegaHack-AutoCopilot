"""
Skill管理工具 - Agent可调用的Skill管理功能
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from langchain.tools import tool
from src.utils.skill_manager import skill_manager


@tool
def list_available_skills() -> str:
    """列出所有可用的Skill扩展功能。
    
    返回所有可安装的Skill列表，包括已安装和未安装的。
    
    Returns:
        可用Skill列表的描述
    """
    skills = skill_manager.list_available_skills()
    
    if not skills:
        return "暂无可用的Skill扩展"
    
    # 分类显示
    categories = {}
    for skill in skills:
        cat = skill["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(skill)
    
    result = ["📦 **可用Skill扩展列表**\n"]
    
    for cat, cat_skills in categories.items():
        result.append(f"\n### {cat}")
        for s in cat_skills:
            status = "✅ 已安装" if s["installed"] else "⬜ 未安装"
            result.append(f"- {s['icon']} **{s['name']}** ({s['name_en']}) {status}")
            result.append(f"  └─ {s['description']}")
    
    result.append("\n\n💡 **安装方法**: 告诉用户 '安装 [Skill名称]' 即可")
    
    return "\n".join(result)


@tool
def install_skill(skill_name: str) -> str:
    """安装指定的Skill扩展功能。
    
    Args:
        skill_name: Skill的英文名称，如: weather, news, email, translation等
        
    Returns:
        安装结果描述
    """
    result = skill_manager.install_skill(skill_name)
    
    if result["success"]:
        return f"""✅ **{result['message']}**

{result['skill']} 已成功安装，现在可以使用该功能了！

使用方法：
- 如果是工具类Skill（如天气、翻译），我会在需要时自动调用
- 如果需要额外配置，我会提示您完成设置"""
    else:
        available = skill_manager.list_available_skills()
        available_names = [s['name_en'] for s in available]
        return f"""❌ **{result['message']}**

可用的Skill名称：{', '.join(available_names)}

示例：安装天气Skill → `install_skill("weather")`"""


@tool
def uninstall_skill(skill_name: str) -> str:
    """卸载指定的Skill扩展功能。
    
    Args:
        skill_name: Skill的英文名称
        
    Returns:
        卸载结果描述
    """
    result = skill_manager.uninstall_skill(skill_name)
    
    if result["success"]:
        return f"✅ **{result['message']}**\n\nSkill已卸载，如需重新安装请告诉我。"
    else:
        return f"❌ **{result['message']}**"


@tool
def list_installed_skills() -> str:
    """列出已安装的Skill扩展功能。
    
    Returns:
        已安装Skill列表描述
    """
    skills = skill_manager.list_installed_skills()
    
    if not skills:
        return """📭 **暂未安装任何Skill扩展**

我可以安装以下扩展来增强能力：
- 🌤️ 天气查询
- 📰 新闻资讯
- 📈 股票查询
- 🌐 翻译助手
- 📧 邮件发送
- 🎨 图片生成
- 📄 文档处理
- 🔢 计算器

告诉我想安装哪个，我来帮你配置！"""
    
    result = [f"✅ **已安装 {len(skills)} 个Skill扩展**\n"]
    
    for s in skills:
        result.append(f"- {s['icon']} **{s['name']}**: {s['instructions']}")
    
    result.append("\n\n💡 如需卸载某Skill，告诉我 '卸载 [Skill名称]' 即可")
    
    return "\n".join(result)


@tool
def execute_weather_query(city: str) -> str:
    """查询指定城市的天气信息。
    
    Args:
        city: 城市名称，如: 北京、上海、东京
        
    Returns:
        天气信息描述
    """
    # 这里模拟天气查询，实际项目中应该调用真实天气API
    weather_data = {
        "北京": {"temp": "26°C", "weather": "晴", "humidity": "45%", "air": "优"},
        "上海": {"temp": "28°C", "weather": "多云", "humidity": "65%", "air": "良"},
        "深圳": {"temp": "30°C", "weather": "雷阵雨", "humidity": "80%", "air": "中"},
        "广州": {"temp": "29°C", "weather": "阴", "humidity": "75%", "air": "良"},
        "杭州": {"temp": "27°C", "weather": "晴", "humidity": "50%", "air": "优"},
    }
    
    city_weather = weather_data.get(city, {
        "temp": "25°C", "weather": "晴间多云", "humidity": "55%", "air": "良"
    })
    
    return f"""🌤️ **{city}实时天气**

- 温度: {city_weather['temp']}
- 天气: {city_weather['weather']}
- 湿度: {city_weather['humidity']}
- 空气质量: {city_weather['air']}

数据更新时间: 今天"""


@tool
def execute_translation(text: str, target_lang: str = "en") -> str:
    """翻译文本到指定语言。
    
    Args:
        text: 要翻译的文本
        target_lang: 目标语言，如: en(英语), ja(日语), ko(韩语), zh(中文)
        
    Returns:
        翻译结果描述
    """
    # 模拟翻译结果
    lang_names = {"en": "英语", "ja": "日语", "ko": "韩语", "fr": "法语", "de": "德语"}
    lang_name = lang_names.get(target_lang, target_lang)
    
    # 实际项目中应该调用翻译API
    return f"""🌐 **翻译结果** ({lang_name})

原文: {text}

译文: [翻译结果]

⚠️ 这是演示结果，实际翻译需要配置翻译API"""


def get_skill_tools():
    """获取所有Skill相关的工具"""
    return [
        list_available_skills,
        install_skill,
        uninstall_skill,
        list_installed_skills,
        execute_weather_query,
        execute_translation
    ]
