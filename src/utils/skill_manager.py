"""
Skill管理器 - 管理Agent的Skill扩展能力
支持动态安装和管理各种Skill，如天气查询、邮件发送等
"""
import json
import os
from typing import Dict, List, Optional

# Skill注册表 - 已支持的Skill列表
SKILL_REGISTRY = {
    "weather": {
        "name": "天气查询",
        "name_en": "weather",
        "description": "查询全球城市的天气预报、空气质量、穿衣指数等",
        "category": "生活服务",
        "icon": "🌤️",
        "enabled": True,
        "instructions": "当用户询问天气、气温、空气质量、穿衣建议时使用此Skill"
    },
    "news": {
        "name": "新闻资讯",
        "name_en": "news",
        "description": "获取最新新闻资讯、热点话题、行业动态",
        "category": "信息查询",
        "icon": "📰",
        "enabled": True,
        "instructions": "当用户询问新闻、热点事件、行业资讯时使用此Skill"
    },
    "stock": {
        "name": "股票查询",
        "name_en": "stock",
        "description": "查询股票实时行情、涨跌趋势、财务数据",
        "category": "金融财经",
        "icon": "📈",
        "enabled": True,
        "instructions": "当用户询问股票价格、涨跌、财报时使用此Skill"
    },
    "translation": {
        "name": "翻译助手",
        "name_en": "translation",
        "description": "支持中英日韩等多语言互译",
        "category": "语言工具",
        "icon": "🌐",
        "enabled": True,
        "instructions": "当用户需要翻译文本或询问翻译相关问题时使用此Skill"
    },
    "email": {
        "name": "邮件发送",
        "name_en": "email",
        "description": "发送邮件给指定收件人，支持附件",
        "category": "办公工具",
        "icon": "📧",
        "enabled": True,
        "instructions": "当用户需要发送邮件时使用此Skill"
    },
    "calculator": {
        "name": "计算器",
        "name_en": "calculator",
        "description": "执行数学计算、单位换算、面积计算等",
        "category": "工具",
        "icon": "🔢",
        "enabled": True,
        "instructions": "当用户需要计算数值或单位换算时使用此Skill"
    },
    "image_generation": {
        "name": "图片生成",
        "name_en": "image_generation",
        "description": "根据文字描述生成图片",
        "category": "创意工具",
        "icon": "🎨",
        "enabled": True,
        "instructions": "当用户需要生成图片、插画、设计素材时使用此Skill"
    },
    "document": {
        "name": "文档处理",
        "name_en": "document",
        "description": "生成PDF、Word、Excel等文档",
        "category": "办公工具",
        "icon": "📄",
        "enabled": True,
        "instructions": "当用户需要生成报告、表格、合同等文档时使用此Skill"
    }
}

class SkillManager:
    """Skill管理器类"""
    
    def __init__(self, storage_path: str = None):
        """
        初始化Skill管理器
        
        Args:
            storage_path: Skill配置存储路径
        """
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data", "skills_config.json"
            )
        self.storage_path = storage_path
        self._ensure_storage_dir()
        self.installed_skills = self._load_installed_skills()
    
    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        storage_dir = os.path.dirname(self.storage_path)
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)
    
    def _load_installed_skills(self) -> Dict:
        """加载已安装的Skill配置"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        # 默认返回所有已启用的Skill
        return {
            name: info for name, info in SKILL_REGISTRY.items()
            if info.get("enabled", False)
        }
    
    def _save_installed_skills(self):
        """保存已安装的Skill配置"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.installed_skills, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存Skill配置失败: {e}")
    
    def list_available_skills(self) -> List[Dict]:
        """获取所有可用的Skill列表"""
        return [
            {
                "name": info["name"],
                "name_en": name,
                "description": info["description"],
                "category": info["category"],
                "icon": info["icon"],
                "installed": name in self.installed_skills
            }
            for name, info in SKILL_REGISTRY.items()
        ]
    
    def list_installed_skills(self) -> List[Dict]:
        """获取已安装的Skill列表"""
        return [
            {
                "name": info["name"],
                "name_en": name,
                "description": info["description"],
                "category": info["category"],
                "icon": info["icon"],
                "instructions": info.get("instructions", "")
            }
            for name, info in self.installed_skills.items()
        ]
    
    def install_skill(self, skill_name: str) -> Dict:
        """
        安装Skill
        
        Args:
            skill_name: Skill名称(英文)
            
        Returns:
            安装结果
        """
        if skill_name in SKILL_REGISTRY:
            if skill_name in self.installed_skills:
                return {
                    "success": False,
                    "message": f"Skill '{skill_name}' 已经安装过了"
                }
            
            self.installed_skills[skill_name] = SKILL_REGISTRY[skill_name]
            self._save_installed_skills()
            return {
                "success": True,
                "message": f"成功安装 Skill '{skill_name}'",
                "skill": self.installed_skills[skill_name]["name"]
            }
        else:
            available = [f"'{k}'" for k in SKILL_REGISTRY.keys()]
            return {
                "success": False,
                "message": f"未找到 Skill '{skill_name}'，可用的Skill: {', '.join(available)}"
            }
    
    def uninstall_skill(self, skill_name: str) -> Dict:
        """
        卸载Skill
        
        Args:
            skill_name: Skill名称(英文)
            
        Returns:
            卸载结果
        """
        if skill_name in self.installed_skills:
            skill_info = self.installed_skills.pop(skill_name)
            self._save_installed_skills()
            return {
                "success": True,
                "message": f"成功卸载 Skill '{skill_info['name']}'"
            }
        else:
            return {
                "success": False,
                "message": f"Skill '{skill_name}' 未安装"
            }
    
    def get_skill_prompt(self) -> str:
        """获取已安装Skill的系统提示词"""
        if not self.installed_skills:
            return ""
        
        skills_text = "\n".join([
            f"- {info['icon']} **{info['name']}**: {info['instructions']}"
            for name, info in self.installed_skills.items()
        ])
        
        return f"""
## 可用Skill扩展能力

当你需要执行特定任务时，可以使用以下已安装的Skill：

{skills_text}

使用Skill方法：在回复中直接调用Skill功能即可。
"""

# 全局Skill管理器实例
skill_manager = SkillManager()
