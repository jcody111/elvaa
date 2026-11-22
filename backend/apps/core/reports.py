import csv
from datetime import datetime
from io import BytesIO
from django.http import HttpResponse
from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema,OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from apps.accounts.permissions import role_perm
from apps.orders.models import Order

def safe(value):
    value=str(value if value is not None else '')
    # Spreadsheet programs may ignore leading whitespace before interpreting a formula.
    dangerous=value.lstrip(' \t\r\n\ufeff').startswith(('=','+','-','@')) or value.startswith(('\t','\r','\n'))
    return "'"+value if dangerous else value

def report_rows(request):
    qs=Order.objects.order_by('-created_at')
    for param,lookup in [('from','created_at__date__gte'),('to','created_at__date__lte')]:
        value=request.query_params.get(param)
        if value:
            try: datetime.strptime(value,'%Y-%m-%d')
            except ValueError: raise ValueError(f'{param} must be YYYY-MM-DD.')
            qs=qs.filter(**{lookup:value})
    rows=[['Order','Date (UTC)','Email','Order status','Payment status','Subtotal','Discount','Shipping','Tax included','Total']]
    for o in qs.iterator():
        rows.append([safe(o.order_number),o.created_at.isoformat(),safe(o.email),safe(o.status),safe(o.payment_status),
                     str(o.subtotal),str(o.discount),str(o.shipping),str(o.tax),str(o.total)])
    return rows

@extend_schema(parameters=[OpenApiParameter('from',OpenApiTypes.DATE,description='Inclusive UTC start date'),OpenApiParameter('to',OpenApiTypes.DATE,description='Inclusive UTC end date')],responses={(200,'text/csv'):OpenApiTypes.BINARY})
@api_view(['GET'])
@permission_classes([role_perm('reports')])
def orders_csv(request):
    try: rows=report_rows(request)
    except ValueError as e: return Response({'detail':str(e)},status=400)
    response=HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition']='attachment; filename="elvaa-orders.csv"'
    writer=csv.writer(response); writer.writerows(rows)
    return response

@extend_schema(parameters=[OpenApiParameter('from',OpenApiTypes.DATE,description='Inclusive UTC start date'),OpenApiParameter('to',OpenApiTypes.DATE,description='Inclusive UTC end date')],responses={(200,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'):OpenApiTypes.BINARY})
@api_view(['GET'])
@permission_classes([role_perm('reports')])
def orders_xlsx(request):
    try: rows=report_rows(request)
    except ValueError as e: return Response({'detail':str(e)},status=400)
    from openpyxl import Workbook
    wb=Workbook(); ws=wb.active; ws.title='Orders'
    for row in rows: ws.append(row)
    out=BytesIO(); wb.save(out)
    response=HttpResponse(out.getvalue(),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition']='attachment; filename="elvaa-orders.xlsx"'
    return response
