import {test,expect} from '@playwright/test'

const username=process.env.ELVAA_E2E_STAFF_USERNAME
const password=process.env.ELVAA_E2E_STAFF_PASSWORD

// Leaves an unsubscribed synthetic address and audit entries. Use a disposable database.
test('staff can manage discount codes and unsubscribe a pending address',async({page})=>{
 test.skip(!username||!password,'Set staff credentials for the isolated marketing test.')
 test.setTimeout(75_000)
 await page.goto('/account')
 await page.locator('#username').fill(username!)
 await page.locator('#password').fill(password!)
 const login=page.waitForResponse(r=>r.url().includes('/api/v1/auth/login/')&&r.request().method()==='POST')
 await page.locator('form').getByRole('button',{name:'SIGN IN'}).click()
 const response=await login;expect(response.status()).toBe(200)
 const headers={Authorization:`Bearer ${(await response.json()).access}`}
 const code=`PROMO${Date.now().toString(36)}${Math.random().toString(36).slice(2,6)}`.toUpperCase()
 const email=`${code.toLowerCase()}@example.test`
 const signup=await page.request.post('/api/v1/newsletter/',{data:{email}})
 expect(signup.status(),await signup.text()).toBe(200)
 try{
  await page.goto('/admin/marketing')
  await page.getByLabel('Search codes').fill(code)
  await page.getByLabel('Code',{exact:true}).fill(code.toLowerCase())
  await page.getByLabel('Value',{exact:true}).fill('15')
  await page.getByLabel('Usage limit (optional)').fill('8')
  await page.getByRole('button',{name:'CREATE CODE'}).click()
  await expect(page.getByText('Discount code created.')).toBeVisible()
  const coupon=page.getByRole('row').filter({has:page.getByRole('cell',{name:code,exact:true})})
  await expect(coupon).toContainText('15.00%')
  await expect(coupon).toContainText('0 / 8')
  await coupon.getByRole('button',{name:'DEACTIVATE'}).click()
  await expect(coupon).toContainText('Inactive')
  await coupon.getByRole('button',{name:'ACTIVATE',exact:true}).click()
  await expect(coupon).toContainText('Active')
  page.once('dialog',dialog=>dialog.accept())
  await coupon.getByRole('button',{name:'DELETE'}).click()
  await expect(coupon).toHaveCount(0)
  await page.getByLabel('Search addresses').fill(email)
  const subscriber=page.locator('tr',{hasText:email})
  await expect(subscriber).toContainText('Pending confirmation')
  page.once('dialog',dialog=>dialog.accept())
  await subscriber.getByRole('button',{name:'UNSUBSCRIBE'}).click()
  await expect(subscriber).toContainText('Unsubscribed')
  await expect(subscriber.getByRole('button',{name:'UNSUBSCRIBE'})).toHaveCount(0)
 }finally{
  const list=await page.request.get(`/api/v1/coupons/?search=${encodeURIComponent(code)}`,{headers})
  if(list.ok()){
   const data=await list.json()
   for(const c of data.results.filter((item:{code:string})=>item.code===code)){
    const removed=await page.request.delete(`/api/v1/coupons/${c.id}/`,{headers})
    if(removed.status()!==204)console.error(`Could not remove test coupon ${code}: ${removed.status()}`)
   }
  }
 }
})
