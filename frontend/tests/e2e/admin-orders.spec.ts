import {randomUUID} from 'node:crypto'
import {test,expect} from '@playwright/test'

const username=process.env.ELVAA_E2E_STAFF_USERNAME
const password=process.env.ELVAA_E2E_STAFF_PASSWORD

// Creates a temporary product and a cancelled demonstration order with audit history.
// Run only against a disposable test database with demo checkout enabled.
test('staff can find an unpaid order, inspect it and cancel its reservation',async({page})=>{
 test.skip(!username||!password||process.env.ELVAA_E2E_DEMO_CHECKOUT!=='1','Provide staff credentials and enable the disposable demo-checkout test.')
 test.setTimeout(90_000)
 await page.goto('/account')
 await page.locator('#username').fill(username!)
 await page.locator('#password').fill(password!)
 const login=page.waitForResponse(r=>r.url().includes('/api/v1/auth/login/')&&r.request().method()==='POST')
 await page.locator('form').getByRole('button',{name:'SIGN IN'}).click()
 const loginResponse=await login;expect(loginResponse.status()).toBe(200)
 const headers={Authorization:`Bearer ${(await loginResponse.json()).access}`}
 const prefix=`ORD${Date.now().toString(36)}${Math.random().toString(36).slice(2,6)}`
 let slug='';let orderId:number|undefined
 try{
  const created=await page.request.post('/api/v1/products/',{headers,data:{name:`${prefix} item`,sku:prefix,price:'32.00',stock:1,is_active:true}})
  expect(created.status(),await created.text()).toBe(201)
  const product=await created.json();slug=product.slug
  const methods=await (await page.request.get('/api/v1/shipping-methods/')).json()
  const checkout=await page.request.post('/api/v1/checkout/',{data:{email:`${prefix}@example.test`,items:[{product_id:product.id,quantity:1}],shipping_method_id:methods.results[0].id,shipping_address:{full_name:'Order Test',street:'Sample Street 1',city:'Berlin',postal_code:'10115',country:'Germany'},payment_method:'manual',idempotency_key:randomUUID()}})
  expect(checkout.status(),await checkout.text()).toBe(201)
  const order=await checkout.json();orderId=order.id
  await page.goto('/admin/orders')
  await page.getByLabel('Search orders').fill(order.order_number)
  const row=page.locator('tr',{hasText:order.order_number})
  await expect(row).toContainText('unpaid')
  await row.getByRole('button',{name:'SHOW DETAILS'}).click()
  await expect(page.getByText(`${prefix}@example.test`)).toBeVisible()
  await expect(page.getByText(`${prefix} item`)).toBeVisible()
  await row.getByLabel(`Status for ${order.order_number}`).selectOption('cancelled')
  await row.getByRole('button',{name:'Save'}).click()
  await expect(row.getByLabel(`Status for ${order.order_number}`)).toHaveValue('cancelled')
  const refreshed=await page.request.get(`/api/v1/products/${slug}/`,{headers})
  expect((await refreshed.json()).stock).toBe(1)
 }finally{
  if(orderId){
   const cancelled=await page.request.post(`/api/v1/orders/${orderId}/status/`,{headers,data:{status:'cancelled'}})
   if(cancelled.status()!==200)console.error(`Could not close test order ${orderId}: ${cancelled.status()}`)
  }
  if(slug){
   const removed=await page.request.delete(`/api/v1/products/${slug}/`,{headers})
   if(removed.status()!==204)console.error(`Could not remove test product ${slug}: ${removed.status()}`)
  }
 }
})
