import './app.css'
import App from './App.svelte'

console.log('Loading Flamelet app...')

try {
  const appDiv = document.getElementById('app')
  console.log('App div found:', !!appDiv)

  const app = new App({
    target: appDiv,
  })
  console.log('Svelte app mounted successfully')
} catch (error) {
  console.error('Error mounting Svelte app:', error)
  // Fallback: show error on page
  const appDiv = document.getElementById('app')
  if (appDiv) {
    appDiv.innerHTML = `<div style="padding: 20px; color: #f85149; font-family: monospace;">
      Error: ${error.message}<br>
      Check console for details
    </div>`
  }
}
