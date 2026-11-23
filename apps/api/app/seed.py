from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import SessionLocal, init_db
from app.models import BookListing, Textbook, User

TEXTBOOKS: list[dict[str, Any]] = [
    {
        "isbn": "9787040554864",
        "title": "高等数学（第七版）上册",
        "author": "同济大学数学系",
        "publisher": "高等教育出版社",
        "edition": "第七版",
        "course_code": "MATH101",
        "course_name": "高等数学",
        "major": "理工类",
        "category": "公共课",
        "new_price": 49.8,
        "description": "理工科基础课程教材，开学季需求集中。",
    },
    {
        "isbn": "9787115546081",
        "title": "Python编程：从入门到实践",
        "author": "Eric Matthes",
        "publisher": "人民邮电出版社",
        "edition": "第3版",
        "course_code": "CS101",
        "course_name": "程序设计基础",
        "major": "计算机",
        "category": "专业课",
        "new_price": 89.8,
        "description": "适合程序设计与人工智能专业入门课程。",
    },
    {
        "isbn": "9787111695851",
        "title": "机器学习",
        "author": "周志华",
        "publisher": "机械工业出版社",
        "edition": "第1版",
        "course_code": "AI201",
        "course_name": "机器学习导论",
        "major": "人工智能",
        "category": "专业课",
        "new_price": 88.0,
        "description": "人工智能专业核心课程教材，常带学习笔记。",
    },
    {
        "isbn": "9787115428028",
        "title": "数据结构（C语言版）",
        "author": "严蔚敏",
        "publisher": "人民邮电出版社",
        "edition": "第2版",
        "course_code": "CS202",
        "course_name": "数据结构",
        "major": "计算机",
        "category": "专业课",
        "new_price": 49.0,
        "description": "计算机与人工智能专业基础教材。",
    },
    {
        "isbn": "9787040572363",
        "title": "大学英语综合教程",
        "author": "李荫华",
        "publisher": "高等教育出版社",
        "edition": "第三版",
        "course_code": "ENG101",
        "course_name": "大学英语",
        "major": "全校",
        "category": "公共课",
        "new_price": 56.0,
        "description": "公共英语课程教材，版本匹配要求较高。",
    },
    {
        "isbn": "9787302577124",
        "title": "人工智能导论",
        "author": "李德毅",
        "publisher": "清华大学出版社",
        "edition": "第2版",
        "course_code": "AI101",
        "course_name": "人工智能导论",
        "major": "人工智能",
        "category": "专业课",
        "new_price": 69.0,
        "description": "人工智能专业通识与导论课程。",
    },
]


def seed_database(db: Session | None = None) -> None:
    owns_session = db is None
    db = db or SessionLocal()
    try:
        users = [
            ("admin@campus.local", "平台管理员", "AdminPass123!", "admin"),
            ("student@campus.local", "林同学", "DemoPass123!", "student"),
            ("seller@campus.local", "顾同学", "DemoPass123!", "student"),
        ]
        user_by_email: dict[str, User] = {}
        for email, display_name, password, role in users:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    email=email,
                    display_name=display_name,
                    password_hash=hash_password(password),
                    role=role,
                )
                db.add(user)
                db.flush()
            user_by_email[email] = user

        textbook_by_isbn: dict[str, Textbook] = {}
        for data in TEXTBOOKS:
            textbook = db.scalar(select(Textbook).where(Textbook.isbn == data["isbn"]))
            if textbook is None:
                textbook = Textbook(**data)
                db.add(textbook)
                db.flush()
            textbook_by_isbn[data["isbn"]] = textbook

        seller = user_by_email["seller@campus.local"]
        listing_specs = [
            ("9787040554864", 8, 18.0, "少量重点划线，附赠课程公式卡。"),
            ("9787115546081", 9, 36.0, "封面完好，前两章有铅笔标注。"),
            ("9787111695851", 7, 28.0, "有章节笔记，正文完整。"),
            ("9787115428028", 9, 22.0, "无缺页，书角轻微磨损。"),
            ("9787302577124", 8, 27.0, "课堂笔记集中在第3—5章。"),
            ("9787040554864", 10, 26.0, "近全新，仅翻看过两次。"),
        ]
        existing_pairs = {
            (item.textbook_id, item.condition_grade, item.asking_price)
            for item in db.scalars(select(BookListing)).all()
        }
        for isbn, grade, price, note in listing_specs:
            textbook = textbook_by_isbn[isbn]
            key = (textbook.id, grade, price)
            if key not in existing_pairs:
                db.add(
                    BookListing(
                        seller_id=seller.id,
                        textbook_id=textbook.id,
                        condition_grade=grade,
                        asking_price=price,
                        note=note,
                        status="active",
                    )
                )
        db.commit()
    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    init_db()
    seed_database()
    print("Seed data is ready.")
