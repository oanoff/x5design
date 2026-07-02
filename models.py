from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Employee:
    telegram_id: str
    full_name: str
    direction: str

@dataclass
class AdminLead:
    telegram_id: str
    role: str  # 'admin' or 'lead'
    direction: Optional[str] = None

@dataclass
class Skill:
    name: str
    group: str
    levels: Dict[str, float]  # {'Младший': 2.0, 'Обычный': 3.0, 'Ведущий': 4.0}

@dataclass
class SurveyResult:
    telegram_id: str
    full_name: str
    direction: str
    date: str
    scores: Dict[str, int]  # {skill_name: score}
    average_score: float
    level: str  # 'Младший', 'Обычный', 'Ведущий'