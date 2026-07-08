from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# 注意：本文件内已定义 User 模型（继承自 AbstractUser），
# 后续 LoginLog/OperationLog/ErrorLog/UserCompetitionView 等模型的
# ForeignKey 直接引用上方的 User 类即可，无需使用 get_user_model()


# 用户模型
class User(AbstractUser):
    ROLE_CHOICES = (
        ('user', '普通用户'),
        ('judge', '评委'),
        ('admin', '管理员'),
    )
    nickname = models.CharField(max_length=20, blank=True, null=True, verbose_name='昵称')
    phone = models.CharField(max_length=11, blank=True, null=True, verbose_name='手机号')
    email = models.EmailField(blank=True, null=True, verbose_name='邮箱')
    intro = models.TextField(max_length=200, blank=True, null=True, verbose_name='个人简介')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user', verbose_name='角色')
    avatar = models.ImageField(upload_to='avatar/', blank=True, null=True, verbose_name='头像')

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.username


# 赛事分类模型
class Category(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name='分类名称')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '赛事分类'
        verbose_name_plural = '赛事分类'

    def __str__(self):
        return self.name


# 赛事模型
class Competition(models.Model):
    LEVEL_CHOICES = (
        ('school', '校级'),
        ('city', '市级'),
        ('province', '省级'),
        ('national', '国家级'),
    )
    STATUS_CHOICES = (
        ('draft', '草稿'),
        ('published', '已发布'),
        ('ended', '已结束'),
    )

    title = models.CharField(max_length=200, verbose_name="竞赛标题")
    category = models.ForeignKey('Category', on_delete=models.CASCADE, verbose_name="分类")
    cover = models.ImageField(upload_to='covers/', blank=True, null=True, verbose_name="封面")
    description = models.TextField(null=True, blank=True, verbose_name="赛事简介")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, verbose_name="等级")
    registration_time = models.DateTimeField(default=timezone.now, verbose_name="报名时间")
    organizer = models.CharField(max_length=100, verbose_name="组织方")
    competition_time = models.DateTimeField(default=timezone.now, verbose_name="竞赛时间")
    location = models.CharField(max_length=200, verbose_name="竞赛地点")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="状态")
    # ✅ 新增：浏览量字段
    view_count = models.IntegerField(default=0, verbose_name="浏览次数")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    # ✅ 新增：评委关联
    judges = models.ManyToManyField(User, related_name='judged_competitions', verbose_name='评委')

    class Meta:
        verbose_name = "赛事"
        verbose_name_plural = "赛事"


# 报名表模型
class Registration(models.Model):
    """赛事报名记录"""
    STATUS_CHOICES = (
        ('normal', '正常'),
        ('canceled', '已取消'),
        ('finished', '已完成'),
    )
    # 核心关联字段（直接用前面定义的模型，不需要导入）
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registrations', verbose_name='报名用户')
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='registrations',
                                    verbose_name='所属赛事')
    # 报名表单字段
    name = models.CharField(max_length=50, verbose_name='报名姓名')
    id_card = models.CharField(max_length=18, verbose_name='身份证号')
    phone = models.CharField(max_length=11, verbose_name='联系电话')
    school = models.CharField(max_length=100, verbose_name='所属学校')
    remark = models.CharField(max_length=200, blank=True, null=True, verbose_name='备注')
    file_url = models.CharField(max_length=500, blank=True, null=True, verbose_name="附件地址")
    # 管理字段
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='normal', verbose_name='报名状态')
    score = models.CharField(max_length=50, blank=True, null=True, verbose_name='赛事成绩')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='报名时间')

    class Meta:
        verbose_name = '报名记录'
        verbose_name_plural = '报名记录'
        unique_together = ('user', 'competition')  # 限制一个用户只能报名同一个赛事一次

    def calculate_final_score(self):
        """计算最终评分"""
        scores = list(self.scores.all().values_list('score', flat=True))
        if not scores:
            return None

        if len(scores) == 1:
            # 只有一个评委
            return float(scores[0])
        elif len(scores) == 2:
            # 两个评委，取平均分
            return float(sum(scores) / 2)
        else:
            # 三个及以上评委，去掉最高分和最低分，再求平均分
            scores_sorted = sorted(scores)
            trimmed_scores = scores_sorted[1:-1]
            return float(sum(trimmed_scores) / len(trimmed_scores))

    def __str__(self):
        return f"{self.name} - {self.competition.title}"


# 评分模型
class Score(models.Model):
    """评委评分记录"""
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='scores',
                                     verbose_name='报名记录')
    judge = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scores', verbose_name='评委')
    score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='评分')
    is_locked = models.BooleanField(default=False, verbose_name='是否锁定')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评分时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '评分记录'
        verbose_name_plural = '评分记录'
        unique_together = ('registration', 'judge')  # 限制一个评委对同一个报名只能评一次

    def __str__(self):
        return f"{self.judge.nickname or self.judge.username} - {self.registration.name}: {self.score}"


# 通知公告模型
class Notice(models.Model):
    title = models.CharField(max_length=200, verbose_name="公告标题")
    content = models.TextField(verbose_name="公告内容")
    create_time = models.DateTimeField(default=timezone.now, verbose_name="发布时间")
    is_published = models.BooleanField(default=True, verbose_name="是否发布")

    class Meta:
        verbose_name = "通知公告"
        verbose_name_plural = "通知公告"
        ordering = ['-create_time']

    def __str__(self):
        return self.title


# 广告模型
class Advertisement(models.Model):
    title = models.CharField(max_length=100, verbose_name='广告标题')
    image = models.ImageField(upload_to='advert/', verbose_name='广告图片')
    link = models.URLField(blank=True, null=True, verbose_name='跳转链接')
    sort = models.IntegerField(default=0, verbose_name='排序')
    status = models.BooleanField(default=True, verbose_name='是否启用')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '广告'
        verbose_name_plural = '广告'
        ordering = ['sort']


# 留言模型
class Message(models.Model):
    title = models.CharField(max_length=100, verbose_name='留言标题')
    content = models.TextField(verbose_name='留言内容')
    name = models.CharField(max_length=20, verbose_name='姓名')
    email = models.EmailField(verbose_name='邮箱')
    phone = models.CharField(max_length=11, blank=True, null=True, verbose_name='手机号')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='留言时间')

    class Meta:
        verbose_name = '留言'
        verbose_name_plural = '留言'
        ordering = ['-create_time']


# 登录日志模型
class LoginLog(models.Model):
    # 登录状态
    STATUS_CHOICES = (
        ('success', '登录成功'),
        ('failed', '登录失败'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="登录用户",
        related_name="login_logs"
    )
    username = models.CharField(max_length=150, verbose_name="登录用户名")
    ip_address = models.GenericIPAddressField(verbose_name="登录IP地址")
    user_agent = models.TextField(verbose_name="浏览器/设备信息")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success', verbose_name="登录状态")
    fail_reason = models.CharField(max_length=200, blank=True, null=True, verbose_name="失败原因")
    login_time = models.DateTimeField(auto_now_add=True, verbose_name="登录时间")

    class Meta:
        verbose_name = "登录日志"
        verbose_name_plural = "登录日志"
        ordering = ['-login_time']  # 按登录时间倒序


# 操作日志模型
class OperationLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="操作用户",
        related_name="operation_logs"
    )
    request_method = models.CharField(max_length=10, verbose_name="请求方式")
    request_url = models.CharField(max_length=255, verbose_name="请求URL")
    ip_address = models.GenericIPAddressField(verbose_name="操作IP地址")
    user_agent = models.TextField(verbose_name="浏览器/设备信息")
    duration = models.IntegerField(verbose_name="请求耗时(ms)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")

    class Meta:
        verbose_name = "操作日志"
        verbose_name_plural = "操作日志"
        ordering = ['-created_at']


# 错误日志模型
class ErrorLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="操作用户",
        related_name="error_logs"
    )
    request_method = models.CharField(max_length=10, verbose_name="请求方式")
    request_url = models.CharField(max_length=255, verbose_name="请求URL")
    ip_address = models.GenericIPAddressField(verbose_name="操作IP地址")
    user_agent = models.TextField(verbose_name="浏览器/设备信息")
    error_message = models.TextField(verbose_name="异常信息")
    error_traceback = models.TextField(verbose_name="异常堆栈")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="发生时间")

    class Meta:
        verbose_name = "错误日志"
        verbose_name_plural = "错误日志"
        ordering = ['-created_at']


# 用户赛事浏览记录（用于防重复统计）
class UserCompetitionView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, verbose_name="赛事")
    viewed_at = models.DateTimeField(auto_now_add=True, verbose_name="浏览时间")

    class Meta:
        verbose_name = "赛事浏览记录"
        verbose_name_plural = "赛事浏览记录"
        indexes = [
            models.Index(fields=['user', 'competition', 'viewed_at']),
        ]