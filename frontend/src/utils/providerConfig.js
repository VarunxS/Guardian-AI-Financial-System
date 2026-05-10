import { API_BASE_URL } from '../config';
import { getUserId } from './auth';

export async function fetchStoredProviderConfig() {
  const res = await fetch(`${API_BASE_URL}/api/settings/config/${getUserId()}`);
  if (!res.ok) {
    throw new Error('Failed to fetch saved provider configuration.');
  }

  const data = await res.json();
  if (!data.configured || !data.api_key) {
    throw new Error('Please configure your API key in Settings first.');
  }

  return data;
}
