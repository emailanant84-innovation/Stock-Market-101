const API = 'http://localhost:8000';

export async function getRankings() {
  return fetch(`${API}/rankings`).then((r) => r.json());
}

export async function syncData() {
  return fetch(`${API}/sync`, { method: 'POST' }).then((r) => r.json());
}

export async function searchStocks(q) {
  return fetch(`${API}/search?q=${encodeURIComponent(q)}`).then((r) => r.json());
}

export async function getStock(ticker) {
  return fetch(`${API}/stock/${encodeURIComponent(ticker)}`).then((r) => r.json());
}

export async function getWishlist() {
  return fetch(`${API}/wishlist`).then((r) => r.json());
}

export async function saveWishlistItem(item) {
  return fetch(`${API}/wishlist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(item),
  }).then((r) => r.json());
}

export async function deleteWishlistItem(ticker) {
  return fetch(`${API}/wishlist/${encodeURIComponent(ticker)}`, { method: 'DELETE' }).then((r) => r.json());
}

export async function recalc(weights) {
  return fetch(`${API}/recalculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(weights),
  }).then((r) => r.json());
}
