export interface ProductImage { id:number; image:string; alt:string; display_order:number }
export interface Variant { id:number; product:number; name:string; sku:string; price:string|null; stock:number; attributes:Record<string,string> }
export interface Product {
  id:number; name:string; slug:string; price:string; compare_at_price:string|null; stock:number; sku:string;
  brand_name:string; category_name:string; category_slug:string; category:number|null; brand:number|null;
  description:string; specifications:Record<string,string>; images:ProductImage[]; variants:Variant[];
  is_active:boolean; is_featured:boolean; is_new:boolean; avg_rating:number|null; review_count:number; created_at:string;
}
export interface Category { id:number; name:string; slug:string; parent:number|null; image_display:string }
export interface Page<T> { count:number; next:string|null; previous:string|null; results:T[] }
export interface User {id:number; username:string; email:string; first_name:string; last_name:string; role:string; is_staff:boolean; is_superuser:boolean; email_verified:boolean}
export interface ShippingMethod {id:number; name:string; price:string; estimated_days:string; free_over_threshold:boolean}
export interface Quote {subtotal:string;discount:string;shipping:string;tax_included:string;total:string;currency:string;shipping_method_id:number}
export interface Order {id:number;order_number:string;status:string;payment_status:string;payment_method:string;email:string;subtotal:string;discount:string;shipping:string;tax:string;total:string;coupon_code:string;shipping_address:Partial<{full_name:string;street:string;city:string;postal_code:string;country:string}>;created_at:string;tracking_number:string;items:{id:number;name:string;variant_name:string;sku:string;quantity:number;unit_price:string;total:string}[]}
export const euro = (n:string|number) => new Intl.NumberFormat('en-DE',{style:'currency',currency:'EUR',maximumFractionDigits:2}).format(Number(n));
