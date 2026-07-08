from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Competition, Category, Registration, Notice, Advertisement, Message, LoginLog, OperationLog, \
    ErrorLog, Score
import re


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'phone', 'email', 'intro', 'role', 'avatar', 'is_active', 'password']
        read_only_fields = ['id']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({'password': '创建用户时密码为必填项'})
        user = User.objects.create_user(**validated_data, password=password)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('用户名或密码错误')
        attrs['user'] = user
        return attrs


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('用户名或密码错误')
        if user.role not in ['admin', 'judge']:
            raise serializers.ValidationError('非管理员或评委账号无法登录后台')
        attrs['user'] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'phone', 'email', 'intro', 'avatar']
        read_only_fields = ['id', 'username']


class CompetitionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    cover = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    judges = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.filter(role='judge'), required=False)
    judges_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Competition
        fields = [
            'id', 'title', 'category', 'category_name', 'cover', 'description',
            'level', 'registration_time', 'organizer', 'competition_time',
            'location', 'status', 'created_at', 'updated_at', 'view_count',
            'judges', 'judges_info'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_judges_info(self, obj):
        judges = obj.judges.all()
        return [{'id': judge.id, 'username': judge.username, 'nickname': judge.nickname or judge.username} for judge in
                judges]


class CategoryOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ['create_time']


class RegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    competition_title = serializers.CharField(source='competition.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    final_score = serializers.SerializerMethodField(read_only=True)
    scores_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Registration
        fields = [
            'id', 'user', 'competition', 'name', 'id_card', 'phone', 'school',
            'remark', 'status', 'score', 'created_at',
            'username', 'competition_title', 'status_display',
            'file_url', 'final_score', 'scores_info'
        ]
        read_only_fields = ['id', 'created_at', 'user', 'status', 'username', 'competition_title', 'status_display']

    def get_final_score(self, obj):
        return obj.calculate_final_score()

    def get_scores_info(self, obj):
        scores = obj.scores.all()
        return [
            {
                'id': score.id,
                'judge_id': score.judge.id,
                'judge_username': score.judge.username,
                'judge_nickname': score.judge.nickname or score.judge.username,
                'score': float(score.score) if score.score else None,
                'is_locked': score.is_locked,
                'created_at': score.created_at.strftime('%Y-%m-%d %H:%M:%S') if score.created_at else None
            }
            for score in scores
        ]


class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ['id', 'title', 'content', 'create_time', 'is_published']


class AdvertisementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advertisement
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Message
        fields = '__all__'


class LoginLogSerializer(serializers.ModelSerializer):
    ip_address = serializers.CharField(read_only=True)
    user_username = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    login_time = serializers.SerializerMethodField(read_only=True)
    fail_reason = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = LoginLog
        fields = '__all__'

    def get_user_username(self, obj):
        return obj.user.username if obj.user else ''

    def get_login_time(self, obj):
        return obj.login_time.strftime('%Y-%m-%d %H:%M:%S')

    def get_fail_reason(self, obj):
        if not obj.fail_reason:
            return '-'
        if 'non_field_errors' in obj.fail_reason:
            match = re.search(r"string='([^']+)'", obj.fail_reason)
            if match:
                return match.group(1)
        return obj.fail_reason


class OperationLogSerializer(serializers.ModelSerializer):
    ip_address = serializers.CharField(read_only=True)
    user_username = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OperationLog
        fields = '__all__'

    def get_user_username(self, obj):
        return obj.user.username if obj.user else '未登录用户'

    def get_created_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')


class ErrorLogSerializer(serializers.ModelSerializer):
    ip_address = serializers.CharField(read_only=True)
    user_username = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ErrorLog
        fields = '__all__'

    def get_user_username(self, obj):
        return obj.user.username if obj.user else '未登录用户'

    def get_created_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')


class ScoreSerializer(serializers.ModelSerializer):
    judge_username = serializers.CharField(source='judge.username', read_only=True)
    judge_nickname = serializers.CharField(source='judge.nickname', read_only=True, allow_null=True)
    registration_name = serializers.CharField(source='registration.name', read_only=True)
    competition_title = serializers.CharField(source='registration.competition.title', read_only=True)

    class Meta:
        model = Score
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
