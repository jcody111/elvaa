from django.urls import path
from . import views, reports
urlpatterns=[path('health/',views.health),path('admin/stats/',views.dashboard_stats),path('settings/store/',views.store_settings),
             path('reports/orders.csv/',reports.orders_csv),path('reports/orders.xlsx/',reports.orders_xlsx)]
