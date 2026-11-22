import {test,expect} from '@playwright/test'

// This creates a demonstration order and cancels its reservation afterward.
// Run only against a disposable seeded test database with demo checkout enabled.
test('guest demo checkout is clearly unpaid and can release its reservation',async({page})=>{
 test.skip(process.env.ELVAA_E2E_DEMO_CHECKOUT!=='1','Set ELVAA_E2E_DEMO_CHECKOUT=1 for the disposable demo-checkout test.')
 test.setTimeout(90_000)
 let checkoutKey=''
 try{
  await page.goto('/product/the-studio-blazer')
  await page.getByRole('button',{name:'M',exact:true}).click()
  await page.getByRole('button',{name:'ADD TO BAG'}).click()
  await page.goto('/checkout')
  await page.locator('#co-email').fill('demo-checkout@example.test')
  await page.getByRole('button',{name:'CONTINUE',exact:false}).click()
  await page.locator('#co-name').fill('Demo Buyer')
  await page.locator('#co-street').fill('Sample Street 1')
  await page.locator('#co-city').fill('Berlin')
  await page.locator('#co-postal').fill('10115')
  await page.getByRole('button',{name:'CONTINUE',exact:false}).click()
  await page.getByRole('heading',{name:'Choose your delivery.'}).waitFor()
  await page.getByRole('button',{name:'CONTINUE',exact:false}).click()
  await page.getByRole('button',{name:'CONTINUE',exact:false}).click()
  await expect(page.getByText('Demo checkout only.')).toBeVisible()
  await page.getByRole('checkbox').check()
  const request=page.waitForRequest(r=>r.url().includes('/api/v1/checkout/')&&r.method()==='POST')
  await page.getByRole('button',{name:'CREATE DEMO ORDER'}).click()
  checkoutKey=(await request).postDataJSON().idempotency_key
  await expect(page.getByText('ORDER REQUEST RECEIVED')).toBeVisible()
  await expect(page.getByText(/not a completed purchase/)).toBeVisible()
 }finally{
  if(checkoutKey){
   const cancelled=await page.request.post('/api/v1/checkout/cancel/',{data:{idempotency_key:checkoutKey}})
   expect(cancelled.status(),await cancelled.text()).toBe(200)
  }
 }
})
