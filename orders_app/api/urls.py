"""URL routes for order API endpoints."""

from django.urls import path

from orders_app.api.views import (
    CompletedOrderCountView,
    OrderCountView,
    OrderListCreateView,
    OrderStatusUpdateView,
)


app_name = 'orders_app'

urlpatterns = [
    path('orders/', OrderListCreateView.as_view(), name='order-create'),
    path('orders/<int:pk>/', OrderStatusUpdateView.as_view(), name='order-detail'),
    path(
        'order-count/<int:business_user_id>/',
        OrderCountView.as_view(),
        name='order-count',
    ),
    path(
        'completed-order-count/<int:business_user_id>/',
        CompletedOrderCountView.as_view(),
        name='completed-order-count',
    ),
]

