from sqlalchemy import Column, Text, DateTime, Integer
from sqlalchemy.sql import func
from core.db import Base

class VEToken(Base):
    __tablename__ = "ve_tokens"
    __table_args__ = {"schema": "viva_engage"}

    id = Column(Text, primary_key=True, default="current")
    access_token = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class VECommunity(Base):
    __tablename__ = "communities"
    __table_args__ = {"schema": "viva_engage"}

    id = Column(Text, primary_key=True)
    group_id = Column(Text)
    display_name = Column(Text)
    description = Column(Text)
    privacy = Column(Text)
    created_at_ve = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class VEReportGroupsActivityCounts(Base):
    __tablename__ = "report_groups_activity_counts"
    __table_args__ = {"schema": "viva_engage"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Text, nullable=False)
    report_refresh_date = Column(Text)
    report_period = Column(Text)
    liked = Column(Integer)
    posted = Column(Integer)
    read = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class VEReportGroupsActivityDetail(Base):
    __tablename__ = "report_groups_activity_detail"
    __table_args__ = {"schema": "viva_engage"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Text)
    group_display_name = Column(Text)
    member_count = Column(Integer)
    posted_count = Column(Integer)
    read_count = Column(Integer)
    liked_count = Column(Integer)
    last_activity_date = Column(Text)
    report_refresh_date = Column(Text)
    report_period = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class VEReportUserActivityDetail(Base):
    __tablename__ = "report_user_activity_detail"
    __table_args__ = {"schema": "viva_engage"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_principal_name = Column(Text)
    display_name = Column(Text)
    user_state = Column(Text)
    state_change_date = Column(Text)
    last_activity_date = Column(Text)
    posted = Column(Integer)
    read = Column(Integer)
    liked = Column(Integer)
    assigned_products = Column(Text)
    report_refresh_date = Column(Text)
    report_period = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class VEReportDeviceUsageUserDetail(Base):
    __tablename__ = "report_device_usage_user_detail"
    __table_args__ = {"schema": "viva_engage"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_principal_name = Column(Text)
    display_name = Column(Text)
    user_state = Column(Text)
    state_change_date = Column(Text)
    report_refresh_date = Column(Text)
    report_period = Column(Text)
    last_activity_date = Column(Text)
    used_web = Column(Integer)
    used_windows_phone = Column(Integer)
    used_android_phone = Column(Integer)
    used_iphone = Column(Integer)
    used_ipad = Column(Integer)
    used_others = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class VEReportUserActivityCounts(Base):
    __tablename__ = "report_user_activity_counts"
    __table_args__ = {"schema": "viva_engage"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Text, nullable=False)
    report_refresh_date = Column(Text)
    report_period = Column(Text)
    liked = Column(Integer)
    posted = Column(Integer)
    read = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
