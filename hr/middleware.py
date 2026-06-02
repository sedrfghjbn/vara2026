from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve


class RoleRequiredMiddleware:
    """Middleware для проверки ролей пользователя"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Проверяем только для авторизованных пользователей
        if request.user.is_authenticated:
            current_path = request.path
            
            # Маршруты только для HR-менеджеров (суперпользователей)
            # Django админка требует is_staff или is_superuser
            if current_path.startswith('/admin/'):
                if not (request.user.is_staff or request.user.is_superuser):
                    messages.error(request, 'У вас нет доступа к админ-панели. Требуются права HR-менеджера.')
                    return redirect('hr:index')
            
            # Маршруты для HR-менеджеров
            # Обычные сотрудники могут просматривать только свои обучения
            if current_path.startswith('/hr/'):
                # Разрешаем доступ к главной странице
                if current_path in ['/hr/', '/']:
                    pass  # Разрешаем всем
                # Разрешаем доступ к просмотру обучений (проверка доступа в view)
                elif '/trainings/' in current_path and 'create' not in current_path and 'edit' not in current_path and 'delete' not in current_path:
                    pass  # Разрешаем, проверка будет в view
                # Все остальные маршруты только для HR-менеджеров
                elif not request.user.is_hr_manager():
                    messages.error(request, 'У вас нет доступа к этой странице.')
                    return redirect('hr:index')
        
        response = self.get_response(request)
        return response

