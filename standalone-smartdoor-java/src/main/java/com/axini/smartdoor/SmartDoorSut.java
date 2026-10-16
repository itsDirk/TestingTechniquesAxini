package com.axini.smartdoor;

// Copyright 2023 Axini B.V. https://www.axini.com, see: LICENSE.txt.

import java.net.InetSocketAddress;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

// Wrapper class to start the SmartDoor SUT.
public class SmartDoorSut {
    private static final Logger logger = LoggerFactory.getLogger(SmartDoorSut.class);

    public static void main(String[] args) {
        String host = "127.0.0.1";
        String port = "3001";

        if (args.length == 2) {
            host = args[0];
            port = args[1];
        } else if (args.length != 0) {
            logger.error("usage: java SmartDoorSut <host> <port>");
            System.exit(1);
        }

        int iport = Integer.parseInt(port);
        InetSocketAddress address = new InetSocketAddress(host, iport);
        SmartDoorServer server = new SmartDoorServer(address);

        logger.info("Starting the SmartDoor SUT at ws://" + host + ":" + port);

        server.start();
    }
}
