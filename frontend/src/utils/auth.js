/**
 * Simple session-based identity management for public deployments.
 * This avoids data clashing when multiple users access the same hosted instance.
 */
export const getUserId = () => {
  let userId = localStorage.getItem('GUARDIAN_USER_ID');
  if (!userId) {
    // Generate a unique ID for this browser session if not present
    userId = 'user_' + Math.random().toString(36).substring(2, 11);
    localStorage.setItem('GUARDIAN_USER_ID', userId);
  }
  return userId;
};

export const resetUserId = () => {
    localStorage.removeItem('GUARDIAN_USER_ID');
    return getUserId();
};
