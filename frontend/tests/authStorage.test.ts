import assert from 'node:assert/strict'

class MemoryStorage {
  private values = new Map<string, string>()

  getItem(key: string) {
    return this.values.get(key) ?? null
  }

  setItem(key: string, value: string) {
    this.values.set(key, value)
  }

  removeItem(key: string) {
    this.values.delete(key)
  }
}

const session = new MemoryStorage()
const local = new MemoryStorage()

Object.defineProperty(globalThis, 'sessionStorage', {
  value: session,
  configurable: true,
})

Object.defineProperty(globalThis, 'localStorage', {
  value: local,
  configurable: true,
})

const { authStorage } = await import('../src/lib/authStorage.ts')

authStorage.setTokens('access-a', 'refresh-a')

assert.equal(authStorage.getAccessToken(), 'access-a')
assert.equal(authStorage.getRefreshToken(), 'refresh-a')
assert.equal(session.getItem('access_token'), 'access-a')
assert.equal(session.getItem('refresh_token'), 'refresh-a')
assert.equal(local.getItem('access_token'), null)
assert.equal(local.getItem('refresh_token'), null)

authStorage.clearTokens()

assert.equal(authStorage.getAccessToken(), null)
assert.equal(authStorage.getRefreshToken(), null)
