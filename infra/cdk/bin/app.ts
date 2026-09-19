#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { devConfig } from "../lib/config/dev-config";
import { AuditStack } from "../lib/stacks/audit-stack";
import { ApplicationStack } from "../lib/stacks/application-stack";
import { AuthenticationStack } from "../lib/stacks/authentication-stack";
import { CertificateStack } from "../lib/stacks/certificate-stack";
import { CiCdIdentityStack } from "../lib/stacks/ci-cd-identity-stack";
import { CloudFrontStack } from "../lib/stacks/cloudfront-stack";
import { ContainerRegistryStack } from "../lib/stacks/container-registry-stack";
import { DatabaseStack } from "../lib/stacks/database-stack";
import { NetworkStack } from "../lib/stacks/network-stack";
import { WafStack } from "../lib/stacks/waf-stack";

const app = new cdk.App();

new AuditStack(app, "DevAuditStack", {
  applicationName: devConfig.applicationName,
  env: {
    region: devConfig.region,
  },
  environmentName: devConfig.environmentName,
});

new CiCdIdentityStack(app, "DevCiCdIdentityStack", {
  env: {
    region: devConfig.region,
  },
});

const regionalCertificateStack = new CertificateStack(
  app,
  "DevRegionalCertificateStack",
  {
    applicationName: devConfig.applicationName,
    domainName: devConfig.albOriginDomainName,
    environmentName: devConfig.environmentName,
    env: {
      region: devConfig.region,
    },
    hostedZoneId: devConfig.hostedZoneId,
    hostedZoneName: devConfig.hostedZoneName,
  },
);

const edgeCertificateStack = new CertificateStack(
  app,
  "DevEdgeCertificateStack",
  {
    applicationName: devConfig.applicationName,
    crossRegionReferences: true,
    domainName: devConfig.frontendDomainName,
    environmentName: devConfig.environmentName,
    env: {
      region: devConfig.edgeRegion,
    },
    hostedZoneId: devConfig.hostedZoneId,
    hostedZoneName: devConfig.hostedZoneName,
    subjectAlternativeNames: devConfig.edgeCertificateSubjectAlternativeNames,
  },
);

const wafStack = new WafStack(app, "DevWafStack", {
  applicationName: devConfig.applicationName,
  crossRegionReferences: true,
  env: {
    region: devConfig.edgeRegion,
  },
  environmentName: devConfig.environmentName,
});

new AuthenticationStack(app, "DevAuthenticationStack", {
  applicationName: devConfig.applicationName,
  crossRegionReferences: true,
  customerAuthDomainName: devConfig.customerAuthDomainName,
  customerOAuthCallbackUrls: devConfig.customerOAuthCallbackUrls,
  customerOAuthLogoutUrls: devConfig.customerOAuthLogoutUrls,
  customerUserPoolDomainPrefix: devConfig.customerUserPoolDomainPrefix,
  edgeCertificate: edgeCertificateStack.certificate,
  environmentName: devConfig.environmentName,
  env: {
    region: devConfig.region,
  },
  hostedZoneId: devConfig.hostedZoneId,
  hostedZoneName: devConfig.hostedZoneName,
  removalPolicy: devConfig.authenticationRemovalPolicy,
  staffAuthDomainName: devConfig.staffAuthDomainName,
  staffOAuthCallbackUrls: devConfig.staffOAuthCallbackUrls,
  staffOAuthLogoutUrls: devConfig.staffOAuthLogoutUrls,
  staffUserPoolDomainPrefix: devConfig.staffUserPoolDomainPrefix,
  systemAdminAuthDomainName: devConfig.systemAdminAuthDomainName,
  systemAdminOAuthCallbackUrls: devConfig.systemAdminOAuthCallbackUrls,
  systemAdminOAuthLogoutUrls: devConfig.systemAdminOAuthLogoutUrls,
  systemAdminUserPoolDomainPrefix: devConfig.systemAdminUserPoolDomainPrefix,
  userPoolDeletionProtection:
    devConfig.authenticationUserPoolDeletionProtection,
});

const containerRegistryStack = new ContainerRegistryStack(
  app,
  "DevContainerRegistryStack",
  {
    applicationName: devConfig.applicationName,
    apiRepositoryEmptyOnDelete: devConfig.apiRepositoryEmptyOnDelete,
    apiRepositoryRemovalPolicy: devConfig.apiRepositoryRemovalPolicy,
    environmentName: devConfig.environmentName,
    env: {
      region: devConfig.region,
    },
  },
);

const networkStack = new NetworkStack(app, "DevNetworkStack", {
  env: {
    region: devConfig.region,
  },
  applicationName: devConfig.applicationName,
  environmentName: devConfig.environmentName,
  vpcCidr: devConfig.vpcCidr,
  publicSubnets: devConfig.publicSubnets,
  privateIngressSubnets: devConfig.privateIngressSubnets,
  applicationSubnets: devConfig.applicationSubnets,
  databaseSubnets: devConfig.databaseSubnets,
});

const applicationStack = new ApplicationStack(app, "DevApplicationStack", {
  albSecurityGroup: networkStack.albSecurityGroup,
  applicationName: devConfig.applicationName,
  applicationSubnets: networkStack.applicationSubnets,
  apiDesiredCount: devConfig.apiDesiredCount,
  certificate: regionalCertificateStack.certificate,
  ecsSecurityGroup: networkStack.ecsSecurityGroup,
  environmentName: devConfig.environmentName,
  env: {
    region: devConfig.region,
  },
  repository: containerRegistryStack.repository,
  internalAlbSubnets: networkStack.internalAlbSubnets,
  taskCpu: devConfig.apiTaskCpu,
  taskMemoryMiB: devConfig.apiTaskMemoryMiB,
  vpc: networkStack.vpc,
});

new DatabaseStack(app, "DevDatabaseStack", {
  applicationName: devConfig.applicationName,
  databaseAllocatedStorage: devConfig.databaseAllocatedStorage,
  databaseAutoMinorVersionUpgrade: devConfig.databaseAutoMinorVersionUpgrade,
  databaseBackupRetentionPeriod: devConfig.databaseBackupRetentionPeriod,
  databaseDeletionProtection: devConfig.databaseDeletionProtection,
  databaseEngineVersion: devConfig.databaseEngineVersion,
  databaseInstanceClass: devConfig.databaseInstanceClass,
  databaseMaxAllocatedStorage: devConfig.databaseMaxAllocatedStorage,
  databaseMultiAz: devConfig.databaseMultiAz,
  databasePreferredBackupWindow: devConfig.databasePreferredBackupWindow,
  databasePreferredMaintenanceWindow:
    devConfig.databasePreferredMaintenanceWindow,
  databaseRemovalPolicy: devConfig.databaseRemovalPolicy,
  databaseSubnetIds: networkStack.databaseSubnetIds,
  databaseStorageType: devConfig.databaseStorageType,
  env: {
    region: devConfig.region,
  },
  environmentName: devConfig.environmentName,
  rdsSecurityGroup: networkStack.rdsSecurityGroup,
});

new CloudFrontStack(app, "DevCloudFrontStack", {
  albSecurityGroupId: networkStack.albSecurityGroup.securityGroupId,
  albOriginDomainName: devConfig.albOriginDomainName,
  applicationName: devConfig.applicationName,
  crossRegionReferences: true,
  edgeCertificate: edgeCertificateStack.certificate,
  environmentName: devConfig.environmentName,
  env: {
    region: devConfig.region,
  },
  frontendBucketAutoDeleteObjects:
    devConfig.frontendBucketAutoDeleteObjects,
  frontendBucketRemovalPolicy: devConfig.frontendBucketRemovalPolicy,
  frontendBucketVersioned: devConfig.frontendBucketVersioned,
  frontendDomainName: devConfig.frontendDomainName,
  hostedZoneId: devConfig.hostedZoneId,
  hostedZoneName: devConfig.hostedZoneName,
  internalAlb: applicationStack.loadBalancer,
  vpcId: networkStack.vpc.vpcId,
  webAclArn: wafStack.webAclArn,
});

app.synth();
