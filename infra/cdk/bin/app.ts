#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { devConfig } from "../lib/config/dev-config";
import { NetworkStack } from "../lib/stacks/network-stack";

const app = new cdk.App();

new NetworkStack(app, "DevNetworkStack", {
  env: {
    region: devConfig.region,
  },
  applicationName: devConfig.applicationName,
  environmentName: devConfig.environmentName,
  vpcCidr: devConfig.vpcCidr,
  publicSubnets: devConfig.publicSubnets,
  privateIngressSubnets: devConfig.privateIngressSubnets,
});

app.synth();
