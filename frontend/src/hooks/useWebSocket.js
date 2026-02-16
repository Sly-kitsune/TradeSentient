import { useState, useEffect, useRef, useCallback } from 'react';

export function useWebSocket(url) {
    const [messages, setMessages] = useState([]);
    const [isConnected, setIsConnected] = useState(false);
    const ws = useRef(null);
    const pingInterval = useRef(null);
    const reconnectTimeout = useRef(null);

    const connect = useCallback(() => {
        try {
            ws.current = new WebSocket(url);

            ws.current.onopen = () => {
                console.log('✓ WebSocket connected');
                setIsConnected(true);

                // Keepalive ping every 25s
                pingInterval.current = setInterval(() => {
                    if (ws.current?.readyState === WebSocket.OPEN) {
                        ws.current.send('ping');
                    }
                }, 25000);
            };

            ws.current.onmessage = (event) => {
                if (event.data === 'pong') return;
                try {
                    const message = JSON.parse(event.data);
                    // Skip subscription confirmations
                    if (message.type === 'subscribed') return;
                    setMessages(prev => [...prev.slice(-500), message]);
                } catch (e) {
                    console.error('Error parsing message:', e);
                }
            };

            ws.current.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.current.onclose = () => {
                console.log('WebSocket disconnected, reconnecting in 3s...');
                setIsConnected(false);
                clearInterval(pingInterval.current);
                reconnectTimeout.current = setTimeout(connect, 3000);
            };
        } catch (e) {
            console.error('WebSocket connection failed:', e);
            reconnectTimeout.current = setTimeout(connect, 3000);
        }
    }, [url]);

    // Subscribe to a specific symbol
    const subscribe = useCallback((symbol) => {
        if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({
                action: 'subscribe_add',
                symbol: symbol,
            }));
        }
    }, []);

    // Subscribe to multiple symbols at once
    const subscribeMany = useCallback((symbols) => {
        if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({
                action: 'subscribe',
                symbols: symbols,
            }));
        }
    }, []);

    // Subscribe to all symbols (no filter)
    const subscribeAll = useCallback(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({
                action: 'subscribe_all',
            }));
        }
    }, []);

    useEffect(() => {
        connect();

        return () => {
            clearInterval(pingInterval.current);
            clearTimeout(reconnectTimeout.current);
            if (ws.current) {
                ws.current.close();
            }
        };
    }, [connect]);

    return { messages, isConnected, subscribe, subscribeMany, subscribeAll };
}
