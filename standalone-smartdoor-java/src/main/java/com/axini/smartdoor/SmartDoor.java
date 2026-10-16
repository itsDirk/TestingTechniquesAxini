package com.axini.smartdoor;

// Copyright 2023 Axini B.V. https://www.axini.com, see: LICENSE.txt.

// This version of the SmartDoor is the Java version of the original Ruby
// version of the (standalone) Smartdoor SUT.

// With respect to the original Ruby version, however, only a single
// instance is retained: the 'Axini' SmartDoor SUT. All other (buggy)
// implementations have been removed and the support for multiple
// manufacturers (via the RESET command) has been deleted as well.

import java.util.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

// Implementation of the SmartDoor SUT.
public class SmartDoor {
    enum State { CLOSED, OPENED, LOCKED, OFF }

    private static final Logger logger = LoggerFactory.getLogger(SmartDoor.class);

    private SmartDoorServer server;
    private State state;
    private int passcode;
    private int attempts;

    public SmartDoor(SmartDoorServer server) {
        this.server = server;
        this.state = State.CLOSED;
        this.passcode = -1;
        this.attempts = 0;
    }

    // Handle the input (i.e., the stimulus).
    public void handleInput(String message) {
        String[] arr = message.split(":");

        String action = arr[0];
        String param = (arr.length == 2) ? arr[1] : null;

        switch (action) {
        case "OPEN"     : open(); break;
        case "CLOSE"    : close(); break;
        case "LOCK"     : lock(param); break;
        case "UNLOCK"   : unlock(param); break;
        case "OPENED":
        case "CLOSED":
        case "LOCKED":
        case "UNLOCKED":
        case "INVALID_COMMAND":
        case "INVALID_PASSCODE":
        case "INCORRECT_PASSCODE": response(); break;
        default:
            server.send("INVALID_COMMAND");
        }
    }

    // Handles the 'open' command.
    private void open() {
        switch(state) {
        case CLOSED:
            server.send("OPENED");
            state = State.OPENED;
            break;

        case OPENED:
            server.send("INVALID_COMMAND");
            break;

        case LOCKED:
            server.send("INVALID_COMMAND");
            break;

        case OFF:
            break;

        default:
            logger.error("ERROR: unknown state");
        }
    }

    // Handles the 'close' command.
    private void close() {
        switch(state) {
        case CLOSED:
            server.send("INVALID_COMMAND");
            break;

        case OPENED:
            server.send("CLOSED");
            state = State.CLOSED;
            break;

        case LOCKED:
            server.send("INVALID_COMMAND");
            break;

        case OFF:
            break;

        default:
            logger.error("ERROR: unknown state");
        }
    }

    // Handles the 'lock' command.
    private void lock(String passcodeParam) {
        if (passcodeParam == null) {
            server.send("INVALID_COMMAND");
            return;
        }

        int passcode = Integer.parseInt(passcodeParam);

        switch(state) {
        case CLOSED:
            if (isInvalidPasscode(passcode)) {
                server.send("INVALID_PASSCODE");
                return;
            }

            server.send("LOCKED");
            this.state = State.LOCKED;
            this.passcode = passcode;
            this.attempts = 0;
            break;

        case OPENED:
            server.send("INVALID_COMMAND");
            break;

        case LOCKED:
            server.send("INVALID_COMMAND");
            break;

        case OFF:
            break;

        default:
            logger.error("ERROR: unknown state");
        }
    }

    // Handles the 'unlock' command.
    private void unlock(String passcodeParam) {
        if (passcodeParam == null) {
            server.send("INVALID_COMMAND");
            return;
        }

        int passcode = Integer.parseInt(passcodeParam);

        switch(state) {
        case CLOSED:
        case OPENED:
            server.send("INVALID_COMMAND");
            break;

        case LOCKED:
            if (isInvalidPasscode(passcode)) {
                server.send("INVALID_PASSCODE");
                return;
            }

            if (this.passcode == passcode) {
                server.send("UNLOCKED");
                this.state = State.CLOSED;
                this.passcode = -1;
                this.attempts = 0;

            } else {
                server.send("INCORRECT_PASSCODE");
                attempts += 1;
                if (attempts == 3) {
                    server.send("SHUT_OFF");
                    state = State.OFF;
                }
            }
            break;

        case OFF:
            break;

        default:
            logger.error("ERROR: unknown state");
        }
    }

    // Handle the case where a response is received (as stimulus).
    private void response() {
        server.send("INVALID_COMMAND");
    }

    private boolean isInvalidPasscode(int passcode) {
        return ((passcode < 0) || (passcode > 9999));
    }
}
