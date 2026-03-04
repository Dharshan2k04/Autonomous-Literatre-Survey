import { useState, useEffect, useRef, useCallback } from 'react'

export function useSurveyChat(surveyId) {
  const [messages, setMessages] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const wsRef = useRef(null)

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const url = `${protocol}://${host}/ws/chat/${surveyId}`
    const ws = new WebSocket(url)

    ws.onopen = () => setIsConnected(true)
    ws.onclose = () => setIsConnected(false)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'typing') {
        setIsTyping(true)
      } else if (data.type === 'message') {
        setIsTyping(false)
        setMessages((prev) => [
          ...prev,
          { role: data.role, content: data.content, id: Date.now() },
        ])
      } else if (data.type === 'error') {
        setIsTyping(false)
        setMessages((prev) => [
          ...prev,
          { role: 'error', content: data.content, id: Date.now() },
        ])
      }
    }

    wsRef.current = ws
  }, [surveyId])

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [connect])

  const sendMessage = useCallback(
    (text) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: text, id: Date.now() },
      ])
      wsRef.current.send(JSON.stringify({ message: text }))
    },
    []
  )

  return { messages, isConnected, isTyping, sendMessage }
}
