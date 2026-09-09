#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { devConfig } from "../lib/config/dev-config";
import { NetworkStack } from "../lib/stacks/network-stack";

const app = new cdk.App();

new NetworkStack(app, "DevNetworkStack", {
  env: {
    region: devConfig.region,
  },
  availabilityZones: devConfig.availabilityZones,
  vpcCidr: devConfig.vpcCidr,
});

app.synth();
