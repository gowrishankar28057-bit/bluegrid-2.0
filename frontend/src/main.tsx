import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('BlueGrid could not find its application root.')
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
