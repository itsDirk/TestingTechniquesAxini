package com.axini.smartdoor;

// Copyright 2023 Axini B.V. https://www.axini.com, see: LICENSE.txt.

import java.net.InetSocketAddress;

import org.java_websocket.WebSocket;
import org.java_websocket.drafts.Draft;
import org.java_websocket.drafts.Draft_6455;
import org.java_websocket.handshake.ClientHandshake;
import org.java_websocket.server.WebSocketServer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

// SmartDoorServer: WebSocket server for the SmartDoor SUT.
public class SmartDoorServer extends WebSocketServer {
    private static Logger logger =
        LoggerFactory.getLogger(SmartDoorServer.class);

    private SmartDoor door;
    private WebSocket clientConnection;

    public SmartDoorServer(InetSocketAddress address) {
        super(address);
        this.door = null;
        this.clientConnection = null;
    }

    @Override
    public void onOpen(WebSocket conn, ClientHandshake handshake) {
        logger.info("Client connected");
        if (clientConnection != null) {
            logger.error("Another client tried to connect to this WebSocketServer");
            conn.close();
        }
        else {
            clientConnection = conn;
            door = new SmartDoor(this);
            logger.info("SmartDoor created");
        }
    }

    @Override
    public void onClose(WebSocket conn, int code, String reason, boolean remote) {
        logger.info("Client disconnected");
        clientConnection = null;
        door = null;
    }

    @Override
    public void onMessage(WebSocket conn, String message) {
        logger.info("Received message: " + message);

        String[] arr = message.split(":");
        String action = arr[0];
        String param = (arr.length == 2) ? arr[1] : null;

        switch(action) {
        case "RESET":
            // We are ignoring any manufacturer param.
            resetSut();
            break;
        default:
            door.handleInput(message);
        }
    }

    @Override
    public void onError(WebSocket conn, Exception ex) {
        logger.error("Error occurred: " + ex.getMessage());
    }

    @Override
    public void onStart() {
        logger.info("Server started!");
        setConnectionLostTimeout(0);
        setConnectionLostTimeout(100);
    }

    public void send(String message) {
        logger.info("Sending message:  " + message);
        if (clientConnection == null)
            logger.error("WebSocket connection is not yet initialised");
        else
            clientConnection.send(message);
    }

    private void resetSut() {
        logger.info("Resetting SUT");
        door = new SmartDoor(this);
        send("RESET_PERFORMED");
    }
}
