from pydantic import BaseModel

class UserStats(BaseModel):
    total: int
    seekers: int
    employers: int
    admins: int

class VacancyStats(BaseModel):
    active: int
    paused: int
    closed: int

class ApplicationStats(BaseModel):
    total: int
    today: int

class ReportStats(BaseModel):
    pending: int

class ReviewStats(BaseModel):
    flagged: int

class AdminPlatformStatsResponse(BaseModel):
    users: UserStats
    vacancies: VacancyStats
    applications: ApplicationStats
    reports: ReportStats
    reviews: ReviewStats
