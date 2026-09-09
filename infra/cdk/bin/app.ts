#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { NetworkStack } from "../lib/stacks/network-stack";

const app = new cdk.App();

new NetworkStack(app, "DevNetworkStack");

app.synth();
