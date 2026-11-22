import {test,expect} from '@playwright/test'

const username=process.env.ELVAA_E2E_STAFF_USERNAME
const password=process.env.ELVAA_E2E_STAFF_PASSWORD

// This creates and deletes isolated products, and leaves immutable audit entries.
// Run only against a disposable test database with an authorized product manager.
test('staff can search and paginate inventory and safely resolve a stock conflict',async({page})=>{
 test.skip(!username||!password,'Set ELVAA_E2E_STAFF_USERNAME and ELVAA_E2E_STAFF_PASSWORD for the isolated staff test.')
 test.setTimeout(120_000)
 await page.goto('/account')
 await page.locator('#username').fill(username!)
 await page.locator('#password').fill(password!)
 const login=page.waitForResponse(r=>r.url().includes('/api/v1/auth/login/')&&r.request().method()==='POST')
 await page.locator('form').getByRole('button',{name:'SIGN IN'}).click()
 const response=await login
 expect(response.status()).toBe(200)
 const {access}=await response.json()
 const headers={Authorization:`Bearer ${access}`}
 const prefix=`E2E${Date.now().toString(36)}${Math.random().toString(36).slice(2,6)}`
 const created:{id:number;slug:string;name:string}[]=[]
 try{
  for(let i=0;i<25;i++){
   const name=`${prefix} ${String(i).padStart(2,'0')}`
   const r=await page.request.post('/api/v1/products/',{headers,data:{name,sku:`${prefix}-${i}`,price:'12.00',stock:0,is_active:true}})
   expect(r.status(),await r.text()).toBe(201)
   created.push(await r.json())
  }
  const target=created[24]
  const variant=await page.request.post('/api/v1/product-variants/',{headers,data:{product:target.id,name:'M',sku:`${prefix}-M`,stock:2,attributes:{size:'M'}}})
  expect(variant.status(),await variant.text()).toBe(201)
  const variantId=(await variant.json()).id
  await page.goto('/admin/inventory')
  await page.getByLabel('Find product').fill(prefix)
  await page.getByRole('button',{name:'SEARCH',exact:true}).click()
  await expect(page.getByText('25 products found · Page 1')).toBeVisible()
  await page.getByRole('button',{name:'NEXT PRODUCTS'}).click()
  await expect(page.getByRole('option',{name:new RegExp(target.name)})).toHaveCount(1)
  await page.getByLabel('Product',{exact:true}).selectOption(String(target.id))
  await page.getByLabel('Variant').selectOption(String(variantId))
  await expect(page.getByText(/Last observed variant quantity/)).toContainText('2')
  const outside=await page.request.post('/api/v1/inventory-adjustments/',{headers,data:{product_id:target.id,variant_id:variantId,expected_stock:2,new_stock:3,reason:`${prefix} external`}})
  expect(outside.status(),await outside.text()).toBe(200)
  await page.getByLabel('New stock quantity').fill('4')
  await page.getByLabel('Reason').fill(`${prefix} counted`)
  await page.getByRole('button',{name:'RECORD ADJUSTMENT'}).click()
  await expect(page.locator('.form-error[role="alert"]')).toContainText('Stock changed')
  await expect(page.getByRole('button',{name:'RECORD ADJUSTMENT'})).toBeDisabled()
  await page.getByRole('button',{name:'REFRESH STOCK'}).click()
  await expect(page.getByText(/Last observed variant quantity/)).toContainText('3')
  await page.getByLabel('New stock quantity').fill('4')
  await page.getByRole('button',{name:'RECORD ADJUSTMENT'}).click()
  await expect(page.getByText('Stock adjustment recorded.')).toBeVisible()
  await expect(page.locator('tr',{hasText:`${prefix} counted`})).toContainText('+1')
  await page.goto('/admin/products')
  await page.getByPlaceholder('Search products or SKU').fill(target.name)
  const row=page.locator('tr',{hasText:target.name})
  await row.getByRole('button',{name:'EDIT'}).click()
  await expect(page.locator('#p-stock')).toBeDisabled()
  await page.locator('#p-description').fill('Edited without replacing stock.')
  await page.getByRole('button',{name:'SAVE PRODUCT'}).click()
  await expect(page.getByText('Product saved.')).toBeVisible()
 }finally{
  for(const p of created){
   const removed=await page.request.delete(`/api/v1/products/${p.slug}/`,{headers})
   if(removed.status()!==204)console.error(`Could not clean up test product ${p.slug}: ${removed.status()}`)
  }
 }
})
